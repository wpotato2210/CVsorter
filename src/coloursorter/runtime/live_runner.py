from __future__ import annotations

import argparse
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

import numpy as np

from coloursorter.bench import (
    Esp32McuTransport,
    LiveConfig,
    LiveFrameSource,
    MockMcuTransport,
    MockTransportConfig,
    SerialMcuTransport,
    SerialTransportConfig,
)
from coloursorter.config import RuntimeConfig
from coloursorter.deploy import (
    CalibratedOpenCvDetectionConfig,
    CaptureBaselineConfig,
    ModelStubDetectionConfig,
    OpenCvDetectionConfig,
    PipelineRunner,
    PreprocessConfig,
    capture_fault_reason,
    build_detection_provider,
    to_canonical_timing_diagnostics,
    CanonicalTimingDiagnostics,
)
from coloursorter.eval.reject_profiles import (
    RejectProfileValidationError,
    default_profile,
    load_reject_profiles,
    selected_thresholds,
)
from coloursorter.model import FrameMetadata
from coloursorter.protocol.constants import CMD_HEARTBEAT


LOGGER = logging.getLogger(__name__)


STALE_FRAME_ERROR_MESSAGE = "STALE_FRAME_DETECTED: camera frames stopped updating"
MAX_REPEATED_FRAMES = 3


def _frame_content_hash(frame_image_bgr: object) -> str:
    if isinstance(frame_image_bgr, np.ndarray):
        return hashlib.blake2s(frame_image_bgr.tobytes(), digest_size=16).hexdigest()
    return hashlib.blake2s(bytes(frame_image_bgr), digest_size=16).hexdigest()


class FrameFreshnessGuard:
    def __init__(self, max_repeats: int = MAX_REPEATED_FRAMES, frame_timeout_ms: float = 0.0) -> None:
        self._last_timestamp_s: float | None = None
        self._last_hash: str | None = None
        self._repeat_count = 0
        self._max_repeats = int(max_repeats)
        self._frame_timeout_s = max(0.0, float(frame_timeout_ms) / 1000.0)

    def check(self, frame_timestamp_s: float, frame_image_bgr: object, capture_time_s: float | None = None) -> None:
        frame_hash = _frame_content_hash(frame_image_bgr)
        timestamp_s = float(frame_timestamp_s)

        if self._last_timestamp_s is not None:
            if timestamp_s <= self._last_timestamp_s:
                raise RuntimeError(STALE_FRAME_ERROR_MESSAGE)
            if self._frame_timeout_s > 0.0 and (timestamp_s - self._last_timestamp_s) > self._frame_timeout_s:
                raise RuntimeError(STALE_FRAME_ERROR_MESSAGE)


        if frame_hash == self._last_hash:
            self._repeat_count += 1
            if self._repeat_count > self._max_repeats:
                raise RuntimeError(STALE_FRAME_ERROR_MESSAGE)
        else:
            self._repeat_count = 0

        self._last_hash = frame_hash
        self._last_timestamp_s = timestamp_s


def _resolve_runtime_reject_thresholds(project_root: Path) -> dict[str, float]:
    profiles_path = project_root / "configs" / "reject_profiles.yaml"
    try:
        profiles, selected_name = load_reject_profiles(profiles_path)
        resolved = selected_thresholds(profiles, selected_name)
    except RejectProfileValidationError as exc:
        resolved = default_profile().thresholds
        LOGGER.warning(
            "Failed to load reject profiles from %s: %s. Falling back to default reject thresholds.",
            profiles_path,
            exc,
        )
    return {key: float(resolved[key]) for key in sorted(resolved)}


@dataclass(frozen=True)
class LiveRuntimeCycleReport:
    frame_id: int
    detection_count: int
    command_count: int
    detect_latency_ms: float
    send_latency_ms: float
    cycle_latency_ms: float
    timing: CanonicalTimingDiagnostics

    @property
    def pipeline_latency_ms(self) -> float:
        return self.timing.pipeline_latency_ms

    @property
    def frame_timestamp_ms(self) -> float:
        return self.timing.frame_timestamp_ms

    @property
    def trigger_offset_ms(self) -> float:
        return self.timing.trigger_offset_ms

    @property
    def actuation_delay_ms(self) -> float:
        return self.timing.actuation_delay_ms

    @property
    def canonical_timing(self) -> CanonicalTimingDiagnostics:
        return self.timing


@dataclass(frozen=True)
class LiveRuntimeRunResult:
    cycle_count: int
    sent_command_count: int
    reports: tuple[LiveRuntimeCycleReport, ...] = ()
    startup_failed: bool = False
    startup_failure_payload: dict[str, str] | None = None
    stale_frame_failed: bool = False
    stale_frame_error_message: str | None = None


@dataclass(frozen=True)
class StartupDiagnosticCheck:
    passed: bool
    reason: str


@dataclass(frozen=True)
class StartupDiagnosticsReport:
    config_and_profile: StartupDiagnosticCheck
    frame_source_frame: StartupDiagnosticCheck
    detector_metadata: StartupDiagnosticCheck
    transport_ping: StartupDiagnosticCheck

    @property
    def all_passed(self) -> bool:
        return (
            self.config_and_profile.passed
            and self.frame_source_frame.passed
            and self.detector_metadata.passed
            and self.transport_ping.passed
        )


def serialize_startup_failure(report: StartupDiagnosticsReport) -> dict[str, str]:
    """Build a deterministic startup failure payload from diagnostics checks."""
    return {
        "status": "startup_failed",
        "config_and_profile": report.config_and_profile.reason,
        "detector_metadata": report.detector_metadata.reason,
        "frame_source_frame": report.frame_source_frame.reason,
        "transport_ping": report.transport_ping.reason,
    }


def _resolve_detection_profile(runtime_config: RuntimeConfig):
    camera_recipe = runtime_config.detection.active_camera_recipe
    lighting_recipe = runtime_config.detection.active_lighting_recipe
    for profile in runtime_config.detection.profiles:
        if profile.camera_recipe == camera_recipe and profile.lighting_recipe == lighting_recipe:
            return profile
    return runtime_config.detection.profiles[0]


def _has_selected_detection_profile(runtime_config: RuntimeConfig) -> bool:
    camera_recipe = runtime_config.detection.active_camera_recipe
    lighting_recipe = runtime_config.detection.active_lighting_recipe
    return any(
        profile.camera_recipe == camera_recipe and profile.lighting_recipe == lighting_recipe
        for profile in runtime_config.detection.profiles
    )


def build_live_detection_provider(runtime_config: RuntimeConfig):
    profile = _resolve_detection_profile(runtime_config)
    return build_detection_provider(
        runtime_config.detection.provider,
        basic_config=OpenCvDetectionConfig(
            min_area_px=profile.opencv_basic.min_area_px,
            reject_red_threshold=profile.opencv_basic.reject_red_threshold,
        ),
        calibrated_config=CalibratedOpenCvDetectionConfig(
            min_area_px=profile.opencv_calibrated.min_area_px,
            reject_hue_min=profile.opencv_calibrated.reject_hue_min,
            reject_hue_max=profile.opencv_calibrated.reject_hue_max,
            reject_saturation_min=profile.opencv_calibrated.reject_saturation_min,
            reject_value_min=profile.opencv_calibrated.reject_value_min,
        ),
        model_stub_config=ModelStubDetectionConfig(reject_threshold=profile.model_stub.reject_threshold),
        preprocess_config=PreprocessConfig(
            enable_normalization=runtime_config.detection.preprocess.enable_normalization,
            target_luma=runtime_config.detection.preprocess.target_luma,
            gray_world_strength=runtime_config.detection.preprocess.gray_world_strength,
        ),
    )


def build_live_transport(runtime_config: RuntimeConfig):
    transport = runtime_config.transport
    if transport.kind == "mock":
        return MockMcuTransport(
            MockTransportConfig(
                max_queue_depth=transport.max_queue_depth,
                base_round_trip_ms=transport.base_round_trip_ms,
                per_item_penalty_ms=transport.per_item_penalty_ms,
            )
        )
    serial_config = SerialTransportConfig(
        port=transport.serial_port,
        baud=transport.serial_baud,
        timeout_s=transport.serial_timeout_s,
    )
    if transport.kind == "serial":
        return SerialMcuTransport(serial_config)
    if transport.kind == "esp32":
        return Esp32McuTransport(serial_config)
    raise ValueError(f"Unsupported transport kind: {transport.kind}")


class LiveRuntimeRunner:
    def __init__(
        self,
        runtime_config_path: str | Path,
        lane_config_path: str | Path = "configs/lane_geometry.yaml",
        calibration_path: str | Path = "configs/calibration.json",
        runtime_reject_thresholds: Mapping[str, float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        now_fn: Callable[[], float] | None = None,
        failure_sink: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        self._runtime_config = RuntimeConfig.load_startup(runtime_config_path)
        if runtime_reject_thresholds is None:
            project_root = Path(__file__).resolve().parents[3]
            resolved_thresholds = _resolve_runtime_reject_thresholds(project_root)
        else:
            resolved_thresholds = {key: float(value) for key, value in sorted(runtime_reject_thresholds.items())}
        self.runtime_reject_thresholds = resolved_thresholds
        if self._runtime_config.frame_source.mode != "live":
            raise ValueError("LiveRuntimeRunner requires frame_source.mode=live")
        self._lane_config_path = lane_config_path
        self._calibration_path = calibration_path
        self._frame_source_config = LiveConfig(
            camera_index=self._runtime_config.camera.camera_index,
            frame_period_s=self._runtime_config.camera.frame_period_s,
        )
        self._capture_baseline = CaptureBaselineConfig()
        self._pipeline: PipelineRunner | None = None
        self._frame_source: LiveFrameSource | None = None
        self._detector = None
        self._transport = None
        self.startup_diagnostics = self._run_startup_diagnostics()
        self._failure_sink = failure_sink
        self._sleep = sleep_fn or time.sleep
        self._now = now_fn or time.perf_counter

    def _run_startup_diagnostics(self) -> StartupDiagnosticsReport:
        selected_profile = _resolve_detection_profile(self._runtime_config)
        profile_matches_active = _has_selected_detection_profile(self._runtime_config)
        if profile_matches_active:
            config_check = StartupDiagnosticCheck(passed=True, reason="runtime_config_loaded profile_resolved")
        else:
            config_check = StartupDiagnosticCheck(
                passed=False,
                reason=(
                    "active_detection_profile_missing "
                    f"fallback={selected_profile.camera_recipe}/{selected_profile.lighting_recipe}"
                ),
            )

        existing_frame_source = getattr(self, "_frame_source", None)
        frame_source = existing_frame_source if existing_frame_source is not None else LiveFrameSource(self._frame_source_config)
        frame_check = StartupDiagnosticCheck(passed=False, reason="frame_capture_not_attempted")
        try:
            frame_source.open()
            frame = frame_source.next_frame()
            if frame is None:
                frame_check = StartupDiagnosticCheck(passed=False, reason="frame_source_returned_none")
            elif not isinstance(frame.image_bgr, np.ndarray):
                frame_check = StartupDiagnosticCheck(passed=False, reason="frame_not_ndarray_bgr")
            elif frame.image_bgr.ndim != 3 or frame.image_bgr.shape[2] != 3:
                frame_check = StartupDiagnosticCheck(
                    passed=False,
                    reason=f"invalid_frame_shape={tuple(frame.image_bgr.shape)} expected=(H,W,3)_bgr",
                )
            elif frame.image_bgr.dtype != np.uint8:
                frame_check = StartupDiagnosticCheck(
                    passed=False,
                    reason=f"invalid_frame_dtype={frame.image_bgr.dtype} expected=uint8_bgr",
                )
            else:
                frame_check = StartupDiagnosticCheck(
                    passed=True,
                    reason=f"frame_ok shape={tuple(frame.image_bgr.shape)} dtype=uint8_bgr",
                )
        except Exception as exc:  # pragma: no cover - exercised via integration errors
            frame_check = StartupDiagnosticCheck(passed=False, reason=f"frame_source_error={exc}")
        finally:
            frame_source.release()

        existing_detector = getattr(self, "_detector", None)
        detector = existing_detector if existing_detector is not None else build_live_detection_provider(self._runtime_config)
        provider_version = str(getattr(detector, "provider_version", "")).strip()
        model_version = str(getattr(detector, "model_version", "")).strip()
        active_config_hash = str(getattr(detector, "active_config_hash", "")).strip()
        missing_metadata_fields = [
            field_name
            for field_name, value in (
                ("provider_version", provider_version),
                ("model_version", model_version),
                ("active_config_hash", active_config_hash),
            )
            if not value
        ]
        metadata_check = StartupDiagnosticCheck(
            passed=not missing_metadata_fields,
            reason=(
                "detector_metadata_present"
                if not missing_metadata_fields
                else f"missing_detector_metadata={','.join(missing_metadata_fields)}"
            ),
        )

        ping_check = StartupDiagnosticCheck(passed=False, reason="transport_ping_not_attempted")
        existing_transport = getattr(self, "_transport", None)
        transport = existing_transport if existing_transport is not None else build_live_transport(self._runtime_config)
        send_command = getattr(transport, "send_command", None)
        if callable(send_command):
            try:
                send_command(CMD_HEARTBEAT)
                ping_check = StartupDiagnosticCheck(passed=True, reason=f"transport_ping_ok command={CMD_HEARTBEAT}")
            except Exception as exc:  # pragma: no cover - exercised via integration errors
                ping_check = StartupDiagnosticCheck(passed=False, reason=f"transport_ping_error={exc}")
        else:
            ping_check = StartupDiagnosticCheck(
                passed=False,
                reason=(
                    "transport_ping_unavailable_send_command_missing "
                    "mock_transport_requires_send_command_for_deterministic_noop"
                ),
            )
        close_transport = getattr(transport, "close", None)
        if callable(close_transport):
            close_transport()

        report = StartupDiagnosticsReport(
            config_and_profile=config_check,
            frame_source_frame=frame_check,
            detector_metadata=metadata_check,
            transport_ping=ping_check,
        )
        LOGGER.info(
            "startup_diagnostics all_passed=%s config=%s frame=%s metadata=%s transport=%s",
            report.all_passed,
            report.config_and_profile.passed,
            report.frame_source_frame.passed,
            report.detector_metadata.passed,
            report.transport_ping.passed,
            extra={
                "startup_diagnostics": {
                    "all_passed": report.all_passed,
                    "config_and_profile": report.config_and_profile.reason,
                    "frame_source_frame": report.frame_source_frame.reason,
                    "detector_metadata": report.detector_metadata.reason,
                    "transport_ping": report.transport_ping.reason,
                }
            },
        )
        for check_name, check in (
            ("config_and_profile", report.config_and_profile),
            ("frame_source_frame", report.frame_source_frame),
            ("detector_metadata", report.detector_metadata),
            ("transport_ping", report.transport_ping),
        ):
            if not check.passed:
                LOGGER.error("startup_diagnostics_failure check=%s reason=%s", check_name, check.reason)
        return report

    def run(
        self,
        max_cycles: int | None = None,
        enable_reporting: bool = False,
        report_callback: Callable[[LiveRuntimeCycleReport], None] | None = None,
    ) -> LiveRuntimeRunResult:
        if not self.startup_diagnostics.all_passed:
            payload = serialize_startup_failure(self.startup_diagnostics)
            if self._failure_sink is not None:
                self._failure_sink(payload)
            LOGGER.error("startup_gate_failed payload=%s", payload)
            return LiveRuntimeRunResult(
                cycle_count=0,
                sent_command_count=0,
                reports=(),
                startup_failed=True,
                startup_failure_payload=payload,
            )

        self._pipeline = PipelineRunner(
            lane_config_path=self._lane_config_path,
            calibration_path=self._calibration_path,
        )
        self._frame_source = LiveFrameSource(self._frame_source_config)
        self._detector = build_live_detection_provider(self._runtime_config)
        self._transport = build_live_transport(self._runtime_config)

        reports: list[LiveRuntimeCycleReport] = []
        cycle_count = 0
        sent_command_count = 0
        cycle_period_s = self._runtime_config.cycle_timing.period_ms / 1000.0

        frame_source = self._frame_source
        detector = self._detector
        pipeline = self._pipeline
        transport = self._transport
        assert frame_source is not None and detector is not None and pipeline is not None and transport is not None

        frame_source.open()
        freshness_guard = FrameFreshnessGuard(
            max_repeats=MAX_REPEATED_FRAMES,
            frame_timeout_ms=self._runtime_config.scheduling_guard.max_frame_staleness_ms,
        )
        stale_frame_error_message: str | None = None
        try:
            while max_cycles is None or cycle_count < max_cycles:
                cycle_start = self._now()
                frame = frame_source.next_frame()
                if frame is None:
                    break
                try:
                    freshness_guard.check(
                        frame_timestamp_s=frame.timestamp_s,
                        frame_image_bgr=frame.image_bgr,
                        capture_time_s=cycle_start,
                    )
                except RuntimeError as exc:
                    stale_frame_error_message = str(exc)
                    LOGGER.error("stale_frame_guard_failed error=%s", stale_frame_error_message)
                    if self._failure_sink is not None:
                        self._failure_sink({"status": "runtime_failed", "reason": stale_frame_error_message})
                    break

                detect_start = self._now()
                detections = detector.detect(frame.image_bgr)
                detect_latency_ms = (self._now() - detect_start) * 1000.0

                pipeline_start = self._now()
                preprocess_metrics = getattr(detector, "last_validation_metrics", {})
                result = pipeline.run(
                    frame=FrameMetadata(
                        frame_id=frame.frame_id,
                        timestamp_s=frame.timestamp_s,
                        image_height_px=frame.image_bgr.shape[0],
                        image_width_px=frame.image_bgr.shape[1],
                    ),
                    detections=detections,
                    thresholds=self.runtime_reject_thresholds,
                    capture_fault_reason=capture_fault_reason(
                        preprocess_metrics,
                        self._capture_baseline,
                    ),
                )
                decision_latency_ms = (self._now() - pipeline_start) * 1000.0

                send_start = self._now()
                for scheduled in result.scheduled_events:
                    transport.send(scheduled.command)
                    sent_command_count += 1
                send_latency_ms = (self._now() - send_start) * 1000.0

                cycle_count += 1
                cycle_latency_ms = (self._now() - cycle_start) * 1000.0
                if enable_reporting:
                    canonical_timing = to_canonical_timing_diagnostics(
                        frame_timestamp_ms=frame.timestamp_s * 1000.0,
                        ingest_latency_ms=0.0,
                        decision_latency_ms=decision_latency_ms,
                        schedule_latency_ms=0.0,
                        transport_latency_ms=send_latency_ms,
                        cycle_latency_ms=cycle_latency_ms,
                    )
                    report = LiveRuntimeCycleReport(
                        frame_id=frame.frame_id,
                        detection_count=len(detections),
                        command_count=len(result.scheduled_events),
                        detect_latency_ms=detect_latency_ms,
                        send_latency_ms=send_latency_ms,
                        cycle_latency_ms=cycle_latency_ms,
                        timing=canonical_timing,
                    )
                    reports.append(report)
                    if report_callback is not None:
                        report_callback(report)

                remaining_s = cycle_period_s - (self._now() - cycle_start)
                if remaining_s > 0.0:
                    self._sleep(remaining_s)
        finally:
            frame_source.release()
            close_transport = getattr(transport, "close", None)
            if callable(close_transport):
                close_transport()

        return LiveRuntimeRunResult(
            cycle_count=cycle_count,
            sent_command_count=sent_command_count,
            reports=tuple(reports),
            stale_frame_failed=stale_frame_error_message is not None,
            stale_frame_error_message=stale_frame_error_message,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live ColourSorter runtime loop")
    parser.add_argument("--runtime-config", default="configs/bench_runtime.yaml")
    parser.add_argument("--lane-config", default="configs/lane_geometry.yaml")
    parser.add_argument("--calibration", default="configs/calibration.json")
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--enable-reporting", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    runner = LiveRuntimeRunner(
        runtime_config_path=args.runtime_config,
        lane_config_path=args.lane_config,
        calibration_path=args.calibration,
    )
    max_cycles = None if args.max_cycles <= 0 else args.max_cycles
    result = runner.run(max_cycles=max_cycles, enable_reporting=args.enable_reporting)
    print(f"cycles={result.cycle_count} sent_commands={result.sent_command_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
