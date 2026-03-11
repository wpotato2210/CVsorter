"""Command-line bench runner for replay and live ColourSorter validation.

This module wires frame sources, detection providers, the deterministic pipeline,
and artifact generation into a single executable workflow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import cv2

from coloursorter.bench import (
    BenchLogEntry,
    BenchMode,
    BenchRunner,
    BenchSafetyConfig,
    EncoderConfig,
    Esp32McuTransport,
    LiveConfig,
    LiveFrameSource,
    MockMcuTransport,
    MockTransportConfig,
    ReplayConfig,
    ReplayFrameSource,
    SerialMcuTransport,
    SerialTransportConfig,
    VirtualEncoder,
    default_scenarios,
    scenarios_from_thresholds,
)
from coloursorter.bench.evaluation import evaluate_logs, write_artifacts
from coloursorter.config import RuntimeConfig
from coloursorter.deploy import (
    CalibratedOpenCvDetectionConfig,
    ModelStubDetectionConfig,
    OpenCvDetectionConfig,
    PipelineRunner,
    PreprocessConfig,
    build_detection_provider,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for a bench execution session."""
    parser = argparse.ArgumentParser(description="Run ColourSorter bench scenarios.")
    parser.add_argument("--mode", choices=[BenchMode.REPLAY.value, BenchMode.LIVE.value], default=BenchMode.REPLAY.value)
    parser.add_argument("--source", default="data", help="Replay source path (directory/video/image).")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--frame-period-s", type=float, default=1.0 / 30.0)
    parser.add_argument("--max-cycles", type=int, default=300)
    parser.add_argument("--scenario", action="append", default=[], help="Scenario profile name; can be repeated.")
    parser.add_argument("--artifact-root", default="artifacts/bench")
    parser.add_argument("--text-report", action="store_true")
    parser.add_argument("--lane-config", default="configs/lane_geometry.yaml")
    parser.add_argument("--calibration", default="configs/calibration.json")
    parser.add_argument("--runtime-config", default="configs/bench_runtime.yaml")
    parser.add_argument("--run-id", default="baseline-run")
    parser.add_argument("--test-batch-id", default="batch-001")
    parser.add_argument("--enable-snapshots", action="store_true")
    parser.add_argument("--ground-truth-manifest", default="")
    parser.add_argument("--detector-provider", default="")
    parser.add_argument("--detector-threshold", type=float, default=-1.0)
    parser.add_argument("--calibration-mode", choices=["fixed", "adaptive"], default="fixed")
    parser.add_argument("--camera-recipe", default="")
    parser.add_argument("--lighting-recipe", default="")
    return parser.parse_args(argv)


def _load_runtime_config(runtime_config_path: str | Path) -> RuntimeConfig | None:
    """Load startup configuration when the provided path exists."""
    config_path = Path(runtime_config_path)
    if not config_path.exists():
        return None
    return RuntimeConfig.load_startup(config_path)


def _load_ground_truth(path: str) -> dict[str, str]:
    """Load an optional object-id to label map from a JSON manifest."""
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_available_scenarios(runtime_config: RuntimeConfig | None):
    """Return scenario definitions from config thresholds or built-in defaults."""
    if runtime_config is None:
        return default_scenarios()
    return scenarios_from_thresholds(runtime_config.scenario_thresholds)


def _build_transport(runtime_config: RuntimeConfig | None):
    """Build bench transport from runtime config or explicit mock fallback."""
    if runtime_config is None:
        return MockMcuTransport(
            MockTransportConfig(
                max_queue_depth=8,
                base_round_trip_ms=2.0,
                per_item_penalty_ms=0.8,
            )
        )

    transport_config = runtime_config.transport
    if transport_config.kind == "mock":
        return MockMcuTransport(
            MockTransportConfig(
                max_queue_depth=transport_config.max_queue_depth,
                base_round_trip_ms=transport_config.base_round_trip_ms,
                per_item_penalty_ms=transport_config.per_item_penalty_ms,
            )
        )

    serial_config = SerialTransportConfig(
        port=transport_config.serial_port,
        baud=transport_config.serial_baud,
        timeout_s=transport_config.serial_timeout_s,
    )
    if transport_config.kind == "serial":
        return SerialMcuTransport(serial_config)
    if transport_config.kind == "esp32":
        return Esp32McuTransport(serial_config)
    raise ValueError(f"Unsupported transport kind: {transport_config.kind}")


def _select_scenarios(names: list[str], runtime_config: RuntimeConfig | None):
    """Resolve scenario names into a concrete scenario tuple.

    Raises:
        ValueError: If any requested scenario name is unknown.
    """
    available = {scenario.name: scenario for scenario in _load_available_scenarios(runtime_config)}
    selected_names = names or ["nominal"]
    missing = [name for name in selected_names if name not in available]
    if missing:
        raise ValueError(f"Unknown scenarios: {', '.join(missing)}")
    return tuple(available[name] for name in selected_names)


def _build_detector(runtime_config: RuntimeConfig | None, provider_override: str, threshold_override: float, camera_recipe: str = "", lighting_recipe: str = ""):
    """Build a detection provider based on config values and optional CLI overrides."""
    if runtime_config is None:
        provider = provider_override or "opencv_basic"
        return build_detection_provider(provider)

    selected_camera = camera_recipe or runtime_config.detection.active_camera_recipe
    selected_lighting = lighting_recipe or runtime_config.detection.active_lighting_recipe
    selected_profile = next(
        profile
        for profile in runtime_config.detection.profiles
        if profile.camera_recipe == selected_camera and profile.lighting_recipe == selected_lighting
    )

    basic = OpenCvDetectionConfig(
        min_area_px=selected_profile.opencv_basic.min_area_px,
        reject_red_threshold=selected_profile.opencv_basic.reject_red_threshold,
    )
    calibrated = CalibratedOpenCvDetectionConfig(
        min_area_px=selected_profile.opencv_calibrated.min_area_px,
        reject_hue_min=selected_profile.opencv_calibrated.reject_hue_min,
        reject_hue_max=selected_profile.opencv_calibrated.reject_hue_max,
        reject_saturation_min=selected_profile.opencv_calibrated.reject_saturation_min,
        reject_value_min=selected_profile.opencv_calibrated.reject_value_min,
    )
    threshold = selected_profile.model_stub.reject_threshold if threshold_override < 0.0 else threshold_override
    model_stub = ModelStubDetectionConfig(reject_threshold=threshold)
    provider = provider_override or runtime_config.detection.provider
    preprocess = PreprocessConfig(
        enable_normalization=runtime_config.detection.preprocess.enable_normalization,
        target_luma=runtime_config.detection.preprocess.target_luma,
        gray_world_strength=runtime_config.detection.preprocess.gray_world_strength,
    )
    return build_detection_provider(
        provider,
        basic_config=basic,
        calibrated_config=calibrated,
        model_stub_config=model_stub,
        preprocess_config=preprocess,
    )


def _snapshot_frame(frame_bgr: object, output_root: Path, frame_id: int, enabled: bool) -> str:
    """Persist a frame snapshot to the artifacts directory when enabled."""
    if not enabled:
        return ""
    frames_dir = output_root / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    path = frames_dir / f"frame_{frame_id:06d}.png"
    cv2.imwrite(str(path), frame_bgr)
    return str(path)


def _build_audit_trail(args: argparse.Namespace) -> tuple[dict[str, object], ...]:
    return (
        {"event": "operator_action", "action": "run_started", "run_id": args.run_id, "test_batch_id": args.test_batch_id},
        {"event": "recipe_selection", "camera_recipe": args.camera_recipe, "lighting_recipe": args.lighting_recipe},
        {"event": "threshold_binding", "detector_provider": args.detector_provider, "detector_threshold": args.detector_threshold},
        {"event": "calibration_binding", "calibration_path": args.calibration, "lane_config_path": args.lane_config},
    )


def _run_cycles(
    args: argparse.Namespace,
    runner: BenchRunner,
    runtime_config: RuntimeConfig | None,
    artifact_root: Path,
    ground_truth_by_object_id: dict[str, str],
) -> tuple[BenchLogEntry, ...]:
    """Execute bench cycles and collect emitted bench log entries."""
    mode = BenchMode(args.mode)
    frame_source = (
        ReplayFrameSource(args.source, ReplayConfig(frame_period_s=args.frame_period_s))
        if mode == BenchMode.REPLAY
        else LiveFrameSource(LiveConfig(camera_index=args.camera_index, frame_period_s=args.frame_period_s))
    )
    frame_source.open()
    detector = _build_detector(runtime_config, args.detector_provider, args.detector_threshold, args.camera_recipe, args.lighting_recipe)
    logs: list[BenchLogEntry] = []
    previous_timestamp_s = 0.0
    try:
        for _ in range(args.max_cycles):
            frame = frame_source.next_frame()
            if frame is None:
                break
            frame_rgb = cv2.cvtColor(frame.image_bgr, cv2.COLOR_BGR2RGB)
            detect_started = time.perf_counter()
            detections = detector.detect(frame.image_bgr)
            detect_latency_ms = (time.perf_counter() - detect_started) * 1000.0
            snapshot_path = _snapshot_frame(frame.image_bgr, artifact_root, frame.frame_id, args.enable_snapshots)
            cycle_logs = runner.process_ingest_payload(
                {
                    "frame_id": frame.frame_id,
                    "timestamp": frame.timestamp_s,
                    "image_shape": [frame_rgb.shape[0], frame_rgb.shape[1], frame_rgb.shape[2]],
                    "detections": detections,
                    "previous_timestamp_s": previous_timestamp_s,
                    "run_id": args.run_id,
                    "test_batch_id": args.test_batch_id,
                    "frame_snapshot_path": snapshot_path,
                    "ground_truth_by_object_id": ground_truth_by_object_id,
                    "captured_monotonic_s": detect_started,
                    "detect_latency_ms": detect_latency_ms,
                    "preprocess_metrics": detector.last_validation_metrics,
                    "detection_provider_version": detector.provider_version,
                    "detection_model_version": detector.model_version,
                    "active_config_hash": detector.active_config_hash,
                }
            )
            logs.extend(cycle_logs)
            previous_timestamp_s = frame.timestamp_s
    finally:
        frame_source.release()
    return tuple(logs)


def main(argv: list[str] | None = None) -> int:
    """Run the bench CLI entry point and return a process-compatible exit code."""
    args = _parse_args(argv)
    runtime_config = _load_runtime_config(args.runtime_config)
    scenarios = _select_scenarios(args.scenario, runtime_config)
    pipeline = PipelineRunner(lane_config_path=Path(args.lane_config), calibration_path=Path(args.calibration))
    transport = _build_transport(runtime_config)
    encoder = EncoderConfig(
        pulses_per_revolution=2048,
        belt_speed_mm_per_s=140.0,
        pulley_circumference_mm=210.0,
        dropout_ratio=0.0,
    )
    safety = None
    if runtime_config is not None:
        safety = BenchSafetyConfig(
            ingest_budget_ms=runtime_config.cycle_latency_budget.ingest_ms,
            detect_budget_ms=runtime_config.cycle_latency_budget.detect_ms,
            decide_budget_ms=runtime_config.cycle_latency_budget.decide_ms,
            send_budget_ms=runtime_config.cycle_latency_budget.send_ms,
            total_budget_ms=runtime_config.cycle_latency_budget.total_ms,
            max_queue_age_ms=runtime_config.scheduling_guard.max_queue_age_ms,
            max_frame_staleness_ms=runtime_config.scheduling_guard.max_frame_staleness_ms,
            timebase_strategy=runtime_config.timebase_alignment.strategy,
            host_to_mcu_offset_ms=runtime_config.timebase_alignment.host_to_mcu_offset_ms,
            jitter_warn_ms=runtime_config.telemetry_alarm.jitter_warn_ms,
            jitter_critical_ms=runtime_config.telemetry_alarm.jitter_critical_ms,
        )
    runner = BenchRunner(pipeline=pipeline, transport=transport, encoder=VirtualEncoder(encoder), safety=safety)

    ground_truth_by_object_id = _load_ground_truth(args.ground_truth_manifest)
    logs = _run_cycles(args, runner, runtime_config, Path(args.artifact_root), ground_truth_by_object_id)
    evaluation = evaluate_logs(logs=logs, scenarios=scenarios)
    config_snapshot = vars(args)
    artifact_dir = write_artifacts(
        logs=logs,
        evaluation=evaluation,
        output_root=args.artifact_root,
        include_text_report=args.text_report,
        config_snapshot=config_snapshot,
        audit_trail=_build_audit_trail(args),
    )
    print(f"artifact_dir={artifact_dir}")
    print(f"overall={'PASS' if evaluation.passed else 'FAIL'}")
    for result in evaluation.scenarios:
        print(f"{result.name}: {'PASS' if result.passed else 'FAIL'} - {result.detail}")
    return 0 if evaluation.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
