from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


from coloursorter.config.enums import (
    HOMING_MODE,
    HOMING_MODE_VALUES,
    MOTION_MODE,
    MOTION_MODE_VALUES,
)
from coloursorter.deploy import DETECTION_PROVIDER_VALUES


class ConfigValidationError(ValueError):
    pass


FRAME_SOURCE_VALUES = ("replay", "live")
BENCH_TRANSPORT_VALUES = ("mock", "serial", "esp32")
QUEUE_CONSUMPTION_VALUES = ("none", "one_per_tick", "all")

DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
DEFAULT_SERIAL_BAUD = 115200
DEFAULT_SERIAL_TIMEOUT_S = 0.100
DEFAULT_MCU_OPTIONS = ("mock", "serial", "esp32")
DEFAULT_BAUD_OPTIONS = (9600, 57600, 115200, 230400)
DEFAULT_LOG_LEVEL_OPTIONS = ("DEBUG", "INFO", "WARN", "ERROR")
MAX_STARTUP_CONFIG_BYTES = 1_000_000
MAX_STARTUP_CONFIG_LINES = 10_000
MAX_YAML_NESTING_DEPTH = 32
MAX_YAML_LINE_LENGTH = 4_096


@dataclass(frozen=True)
class FrameSourceConfig:
    mode: str
    replay_path: str
    replay_frame_period_s: float
    simulated_overlay: bool


@dataclass(frozen=True)
class CameraConfig:
    camera_index: int
    frame_period_s: float


@dataclass(frozen=True)
class TransportConfig:
    kind: str
    max_queue_depth: int
    base_round_trip_ms: float
    per_item_penalty_ms: float
    serial_port: str
    serial_baud: int
    serial_timeout_s: float


@dataclass(frozen=True)
class CycleTimingConfig:
    period_ms: int
    queue_consumption_policy: str


@dataclass(frozen=True)
class CycleLatencyBudgetConfig:
    ingest_ms: float
    detect_ms: float
    decide_ms: float
    send_ms: float
    total_ms: float


@dataclass(frozen=True)
class SchedulingGuardConfig:
    max_queue_age_ms: float
    max_frame_staleness_ms: float


@dataclass(frozen=True)
class TimebaseAlignmentConfig:
    strategy: str
    host_to_mcu_offset_ms: float


@dataclass(frozen=True)
class TelemetryAlarmConfig:
    jitter_warn_ms: float
    jitter_critical_ms: float


@dataclass(frozen=True)
class ScenarioThresholdsConfig:
    nominal_max_avg_rtt_ms: float
    nominal_max_peak_rtt_ms: float
    stress_max_avg_rtt_ms: float
    stress_max_peak_rtt_ms: float
    fault_max_avg_rtt_ms: float
    fault_max_peak_rtt_ms: float


@dataclass(frozen=True)
class OpenCvBasicDetectionConfig:
    min_area_px: int
    reject_red_threshold: int


@dataclass(frozen=True)
class OpenCvCalibratedDetectionConfig:
    min_area_px: int
    reject_hue_min: int
    reject_hue_max: int
    reject_saturation_min: int
    reject_value_min: int


@dataclass(frozen=True)
class ModelStubProviderConfig:
    reject_threshold: float


@dataclass(frozen=True)
class DetectionProfileConfig:
    camera_recipe: str
    lighting_recipe: str
    opencv_basic: OpenCvBasicDetectionConfig
    opencv_calibrated: OpenCvCalibratedDetectionConfig
    model_stub: ModelStubProviderConfig


@dataclass(frozen=True)
class PreprocessConfig:
    enable_normalization: bool
    target_luma: float
    gray_world_strength: float


@dataclass(frozen=True)
class DetectionConfig:
    provider: str
    active_camera_recipe: str
    active_lighting_recipe: str
    profiles: tuple[DetectionProfileConfig, ...]
    preprocess: PreprocessConfig


@dataclass(frozen=True)
class BaselineRunConfig:
    detector_threshold: float
    calibration_mode: str


@dataclass(frozen=True)
class ManualServoConfig:
    default_lane: int
    default_position_mm: float
    min_lane: int
    max_lane: int
    min_position_mm: float
    max_position_mm: float


@dataclass(frozen=True)
class BenchGuiConfig:
    mcu_options: tuple[str, ...]
    com_port_options: tuple[str, ...]
    baud_options: tuple[int, ...]
    log_level_options: tuple[str, ...]
    default_log_level: str
    manual_servo: ManualServoConfig


@dataclass(frozen=True)
class RuntimeConfig:
    motion_mode: str
    homing_mode: str
    frame_source: FrameSourceConfig
    camera: CameraConfig
    transport: TransportConfig
    cycle_timing: CycleTimingConfig
    cycle_latency_budget: CycleLatencyBudgetConfig
    scheduling_guard: SchedulingGuardConfig
    timebase_alignment: TimebaseAlignmentConfig
    telemetry_alarm: TelemetryAlarmConfig
    scenario_thresholds: ScenarioThresholdsConfig
    detection: DetectionConfig
    baseline_run: BaselineRunConfig
    bench_gui: BenchGuiConfig

    @classmethod
    def from_text(cls, raw_text: str) -> "RuntimeConfig":
        payload = _parse_simple_yaml(raw_text)
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeConfig":
        motion_mode = _required_str(payload, MOTION_MODE)
        homing_mode = _required_str(payload, HOMING_MODE)
        _validate_enum(MOTION_MODE, motion_mode, MOTION_MODE_VALUES)
        _validate_enum(HOMING_MODE, homing_mode, HOMING_MODE_VALUES)

        frame_payload = _required_map(payload, "frame_source")
        frame_mode = _required_str(frame_payload, "mode")
        _validate_enum("frame_source.mode", frame_mode, FRAME_SOURCE_VALUES)
        replay_path = _required_str(frame_payload, "replay_path")
        replay_frame_period_s = _required_float(frame_payload, "replay_frame_period_s")
        _validate_range("frame_source.replay_frame_period_s", replay_frame_period_s, min_value=0.001)
        simulated_overlay = _optional_bool(frame_payload, "simulated_overlay", False)

        camera_payload = _required_map(payload, "camera")
        camera_index = _required_int(camera_payload, "index")
        _validate_range("camera.index", camera_index, min_value=0)
        camera_frame_period_s = _required_float(camera_payload, "frame_period_s")
        _validate_range("camera.frame_period_s", camera_frame_period_s, min_value=0.001)

        transport_payload = _required_map(payload, "transport")
        transport_kind = _required_str(transport_payload, "kind")
        _validate_enum("transport.kind", transport_kind, BENCH_TRANSPORT_VALUES)
        max_queue_depth = _required_int(transport_payload, "max_queue_depth")
        base_round_trip_ms = _required_float(transport_payload, "base_round_trip_ms")
        per_item_penalty_ms = _required_float(transport_payload, "per_item_penalty_ms")
        _validate_range("transport.max_queue_depth", max_queue_depth, min_value=1)
        _validate_range("transport.base_round_trip_ms", base_round_trip_ms, min_value=0.0)
        _validate_range("transport.per_item_penalty_ms", per_item_penalty_ms, min_value=0.0)

        serial_payload = _required_map(transport_payload, "serial")
        serial_port = _optional_str(serial_payload, "port", DEFAULT_SERIAL_PORT)
        if not serial_port:
            raise ConfigValidationError("transport.serial.port is required")
        serial_baud = _optional_int(serial_payload, "baud", DEFAULT_SERIAL_BAUD)
        serial_timeout_s = _optional_float(serial_payload, "timeout_s", DEFAULT_SERIAL_TIMEOUT_S)
        _validate_range("transport.serial.baud", serial_baud, min_value=1)
        _validate_range("transport.serial.timeout_s", serial_timeout_s, min_value=0.001)
        _validate_serial_dependency(transport_kind)

        cycle_payload = _required_map(payload, "cycle_timing")
        period_ms = _required_int(cycle_payload, "period_ms")
        queue_consumption_policy = _required_str(cycle_payload, "queue_consumption_policy")
        _validate_range("cycle_timing.period_ms", period_ms, min_value=1)
        _validate_enum("cycle_timing.queue_consumption_policy", queue_consumption_policy, QUEUE_CONSUMPTION_VALUES)

        budget_payload = _required_map(payload, "cycle_latency_budget")
        cycle_latency_budget = CycleLatencyBudgetConfig(
            ingest_ms=_required_float(budget_payload, "ingest_ms"),
            detect_ms=_required_float(budget_payload, "detect_ms"),
            decide_ms=_required_float(budget_payload, "decide_ms"),
            send_ms=_required_float(budget_payload, "send_ms"),
            total_ms=_required_float(budget_payload, "total_ms"),
        )
        _validate_range("cycle_latency_budget.ingest_ms", cycle_latency_budget.ingest_ms, min_value=0.1)
        _validate_range("cycle_latency_budget.detect_ms", cycle_latency_budget.detect_ms, min_value=0.1)
        _validate_range("cycle_latency_budget.decide_ms", cycle_latency_budget.decide_ms, min_value=0.1)
        _validate_range("cycle_latency_budget.send_ms", cycle_latency_budget.send_ms, min_value=0.1)
        _validate_range("cycle_latency_budget.total_ms", cycle_latency_budget.total_ms, min_value=0.1)

        guards_payload = _required_map(payload, "scheduling_guard")
        scheduling_guard = SchedulingGuardConfig(
            max_queue_age_ms=_required_float(guards_payload, "max_queue_age_ms"),
            max_frame_staleness_ms=_required_float(guards_payload, "max_frame_staleness_ms"),
        )
        _validate_range("scheduling_guard.max_queue_age_ms", scheduling_guard.max_queue_age_ms, min_value=0.0)
        _validate_range("scheduling_guard.max_frame_staleness_ms", scheduling_guard.max_frame_staleness_ms, min_value=0.0)

        timebase_payload = _required_map(payload, "timebase_alignment")
        strategy = _required_str(timebase_payload, "strategy")
        _validate_enum("timebase_alignment.strategy", strategy, ("encoder_epoch", "host_to_mcu_offset"))
        host_to_mcu_offset_ms = _required_float(timebase_payload, "host_to_mcu_offset_ms")
        _validate_range("timebase_alignment.host_to_mcu_offset_ms", host_to_mcu_offset_ms, min_value=0.0)
        timebase_alignment = TimebaseAlignmentConfig(strategy=strategy, host_to_mcu_offset_ms=host_to_mcu_offset_ms)

        alarm_payload = _required_map(payload, "telemetry_alarm")
        telemetry_alarm = TelemetryAlarmConfig(
            jitter_warn_ms=_required_float(alarm_payload, "jitter_warn_ms"),
            jitter_critical_ms=_required_float(alarm_payload, "jitter_critical_ms"),
        )
        _validate_range("telemetry_alarm.jitter_warn_ms", telemetry_alarm.jitter_warn_ms, min_value=0.0)
        _validate_range("telemetry_alarm.jitter_critical_ms", telemetry_alarm.jitter_critical_ms, min_value=telemetry_alarm.jitter_warn_ms)

        thresholds_payload = _required_map(payload, "scenario_thresholds")
        scenario_thresholds = ScenarioThresholdsConfig(
            nominal_max_avg_rtt_ms=_required_float(thresholds_payload, "nominal_max_avg_rtt_ms"),
            nominal_max_peak_rtt_ms=_required_float(thresholds_payload, "nominal_max_peak_rtt_ms"),
            stress_max_avg_rtt_ms=_required_float(thresholds_payload, "stress_max_avg_rtt_ms"),
            stress_max_peak_rtt_ms=_required_float(thresholds_payload, "stress_max_peak_rtt_ms"),
            fault_max_avg_rtt_ms=_required_float(thresholds_payload, "fault_max_avg_rtt_ms"),
            fault_max_peak_rtt_ms=_required_float(thresholds_payload, "fault_max_peak_rtt_ms"),
        )
        _validate_range("scenario_thresholds.nominal_max_avg_rtt_ms", scenario_thresholds.nominal_max_avg_rtt_ms, min_value=0.0)
        _validate_range("scenario_thresholds.nominal_max_peak_rtt_ms", scenario_thresholds.nominal_max_peak_rtt_ms, min_value=0.0)
        _validate_range("scenario_thresholds.stress_max_avg_rtt_ms", scenario_thresholds.stress_max_avg_rtt_ms, min_value=0.0)
        _validate_range("scenario_thresholds.stress_max_peak_rtt_ms", scenario_thresholds.stress_max_peak_rtt_ms, min_value=0.0)
        _validate_range("scenario_thresholds.fault_max_avg_rtt_ms", scenario_thresholds.fault_max_avg_rtt_ms, min_value=0.0)
        _validate_range("scenario_thresholds.fault_max_peak_rtt_ms", scenario_thresholds.fault_max_peak_rtt_ms, min_value=0.0)

        detection_payload = _required_map(payload, "detection")
        provider = _required_str(detection_payload, "provider")
        _validate_enum("detection.provider", provider, DETECTION_PROVIDER_VALUES)

        preprocess_payload = detection_payload.get("preprocess", {})
        if preprocess_payload and not isinstance(preprocess_payload, dict):
            raise ConfigValidationError("detection.preprocess must be a mapping")
        preprocess = PreprocessConfig(
            enable_normalization=_optional_bool(preprocess_payload, "enable_normalization", True),
            target_luma=_optional_float(preprocess_payload, "target_luma", 128.0),
            gray_world_strength=_optional_float(preprocess_payload, "gray_world_strength", 0.6),
        )
        _validate_range("detection.preprocess.target_luma", preprocess.target_luma, min_value=1.0, max_value=255.0)
        _validate_range("detection.preprocess.gray_world_strength", preprocess.gray_world_strength, min_value=0.0, max_value=1.0)

        active_camera_recipe = _optional_str(detection_payload, "active_camera_recipe", "default")
        active_lighting_recipe = _optional_str(detection_payload, "active_lighting_recipe", "default")

        profiles_payload = detection_payload.get("profiles")
        if profiles_payload is None:
            profiles_payload = [
                {
                    "camera_recipe": "default",
                    "lighting_recipe": "default",
                    "opencv_basic": _required_map(detection_payload, "opencv_basic"),
                    "opencv_calibrated": _required_map(detection_payload, "opencv_calibrated"),
                    "model_stub": _required_map(detection_payload, "model_stub"),
                }
            ]
        if isinstance(profiles_payload, dict):
            profiles_payload = list(profiles_payload.values())
        if not isinstance(profiles_payload, list) or not profiles_payload:
            raise ConfigValidationError("detection.profiles must be a non-empty list")

        profiles: list[DetectionProfileConfig] = []
        for profile in profiles_payload:
            if not isinstance(profile, dict):
                raise ConfigValidationError("detection.profiles entries must be mappings")
            camera_recipe = _required_str(profile, "camera_recipe")
            lighting_recipe = _required_str(profile, "lighting_recipe")

            basic_payload = _required_map(profile, "opencv_basic")
            basic = OpenCvBasicDetectionConfig(
                min_area_px=_required_int(basic_payload, "min_area_px"),
                reject_red_threshold=_required_int(basic_payload, "reject_red_threshold"),
            )
            _validate_range("detection.opencv_basic.min_area_px", basic.min_area_px, min_value=1)
            _validate_range("detection.opencv_basic.reject_red_threshold", basic.reject_red_threshold, min_value=0, max_value=255)

            calibrated_payload = _required_map(profile, "opencv_calibrated")
            calibrated = OpenCvCalibratedDetectionConfig(
                min_area_px=_required_int(calibrated_payload, "min_area_px"),
                reject_hue_min=_required_int(calibrated_payload, "reject_hue_min"),
                reject_hue_max=_required_int(calibrated_payload, "reject_hue_max"),
                reject_saturation_min=_required_int(calibrated_payload, "reject_saturation_min"),
                reject_value_min=_required_int(calibrated_payload, "reject_value_min"),
            )
            _validate_range("detection.opencv_calibrated.min_area_px", calibrated.min_area_px, min_value=1)
            _validate_range("detection.opencv_calibrated.reject_hue_min", calibrated.reject_hue_min, min_value=0, max_value=179)
            _validate_range("detection.opencv_calibrated.reject_hue_max", calibrated.reject_hue_max, min_value=0, max_value=179)
            if calibrated.reject_hue_min > calibrated.reject_hue_max:
                raise ConfigValidationError("detection.opencv_calibrated.reject_hue_min must be <= reject_hue_max")
            _validate_range("detection.opencv_calibrated.reject_saturation_min", calibrated.reject_saturation_min, min_value=0, max_value=255)
            _validate_range("detection.opencv_calibrated.reject_value_min", calibrated.reject_value_min, min_value=0, max_value=255)

            model_stub_payload = _required_map(profile, "model_stub")
            model_stub = ModelStubProviderConfig(reject_threshold=_required_float(model_stub_payload, "reject_threshold"))
            _validate_range("detection.model_stub.reject_threshold", model_stub.reject_threshold, min_value=0.0, max_value=1.0)
            profiles.append(DetectionProfileConfig(
                camera_recipe=camera_recipe,
                lighting_recipe=lighting_recipe,
                opencv_basic=basic,
                opencv_calibrated=calibrated,
                model_stub=model_stub,
            ))

        if not any(p.camera_recipe == active_camera_recipe and p.lighting_recipe == active_lighting_recipe for p in profiles):
            raise ConfigValidationError("detection active recipe does not match any configured profile")

        baseline_payload = _required_map(payload, "baseline_run")
        detector_threshold = _required_float(baseline_payload, "detector_threshold")
        _validate_range("baseline_run.detector_threshold", detector_threshold, min_value=0.0, max_value=1.0)
        calibration_mode = _required_str(baseline_payload, "calibration_mode")
        _validate_enum("baseline_run.calibration_mode", calibration_mode, ("fixed", "adaptive"))

        gui_payload = payload.get("bench_gui")
        if gui_payload is not None and not isinstance(gui_payload, dict):
            raise ConfigValidationError("bench_gui must be a mapping when provided")
        gui_payload = gui_payload or {}

        serial_options_payload = gui_payload.get("serial_options")
        if serial_options_payload is not None and not isinstance(serial_options_payload, dict):
            raise ConfigValidationError("bench_gui.serial_options must be a mapping when provided")
        serial_options_payload = serial_options_payload or {}

        mcu_options = _optional_list_of_str(serial_options_payload, "mcu_options", DEFAULT_MCU_OPTIONS)
        if not mcu_options:
            raise ConfigValidationError("bench_gui.serial_options.mcu_options must not be empty")

        com_port_options = _optional_list_of_str(serial_options_payload, "com_port_options", (serial_port,))
        if not com_port_options:
            raise ConfigValidationError("bench_gui.serial_options.com_port_options must not be empty")

        baud_options = _optional_list_of_int(serial_options_payload, "baud_options", DEFAULT_BAUD_OPTIONS)
        if not baud_options:
            raise ConfigValidationError("bench_gui.serial_options.baud_options must not be empty")
        for baud in baud_options:
            _validate_range("bench_gui.serial_options.baud_options[]", baud, min_value=1)

        logging_payload = gui_payload.get("logging")
        if logging_payload is not None and not isinstance(logging_payload, dict):
            raise ConfigValidationError("bench_gui.logging must be a mapping when provided")
        logging_payload = logging_payload or {}
        log_level_options = _optional_list_of_str(logging_payload, "levels", DEFAULT_LOG_LEVEL_OPTIONS)
        if not log_level_options:
            raise ConfigValidationError("bench_gui.logging.levels must not be empty")
        default_log_level = _optional_str(logging_payload, "default_level", log_level_options[0])
        if default_log_level not in log_level_options:
            raise ConfigValidationError("bench_gui.logging.default_level must be present in bench_gui.logging.levels")

        manual_payload = gui_payload.get("manual_servo")
        if manual_payload is not None and not isinstance(manual_payload, dict):
            raise ConfigValidationError("bench_gui.manual_servo must be a mapping when provided")
        manual_payload = manual_payload or {}
        min_lane = _optional_int(manual_payload, "min_lane", 0)
        max_lane = _optional_int(manual_payload, "max_lane", 7)
        _validate_range("bench_gui.manual_servo.min_lane", min_lane, min_value=0)
        _validate_range("bench_gui.manual_servo.max_lane", max_lane, min_value=min_lane)
        default_lane = _optional_int(manual_payload, "default_lane", min_lane)
        _validate_range("bench_gui.manual_servo.default_lane", default_lane, min_value=min_lane, max_value=max_lane)

        min_position_mm = _optional_float(manual_payload, "min_position_mm", 0.0)
        max_position_mm = _optional_float(manual_payload, "max_position_mm", 1000.0)
        _validate_range("bench_gui.manual_servo.min_position_mm", min_position_mm, min_value=0.0)
        _validate_range("bench_gui.manual_servo.max_position_mm", max_position_mm, min_value=min_position_mm)
        default_position_mm = _optional_float(manual_payload, "default_position_mm", 100.0)
        _validate_range(
            "bench_gui.manual_servo.default_position_mm",
            default_position_mm,
            min_value=min_position_mm,
            max_value=max_position_mm,
        )

        return cls(
            motion_mode=motion_mode,
            homing_mode=homing_mode,
            frame_source=FrameSourceConfig(
                mode=frame_mode,
                replay_path=replay_path,
                replay_frame_period_s=replay_frame_period_s,
                simulated_overlay=simulated_overlay,
            ),
            camera=CameraConfig(camera_index=camera_index, frame_period_s=camera_frame_period_s),
            transport=TransportConfig(
                kind=transport_kind,
                max_queue_depth=max_queue_depth,
                base_round_trip_ms=base_round_trip_ms,
                per_item_penalty_ms=per_item_penalty_ms,
                serial_port=serial_port,
                serial_baud=serial_baud,
                serial_timeout_s=serial_timeout_s,
            ),
            cycle_timing=CycleTimingConfig(period_ms=period_ms, queue_consumption_policy=queue_consumption_policy),
            cycle_latency_budget=cycle_latency_budget,
            scheduling_guard=scheduling_guard,
            timebase_alignment=timebase_alignment,
            telemetry_alarm=telemetry_alarm,
            scenario_thresholds=scenario_thresholds,
            detection=DetectionConfig(
                provider=provider,
                active_camera_recipe=active_camera_recipe,
                active_lighting_recipe=active_lighting_recipe,
                profiles=tuple(profiles),
                preprocess=preprocess,
            ),
            baseline_run=BaselineRunConfig(
                detector_threshold=detector_threshold,
                calibration_mode=calibration_mode,
            ),
            bench_gui=BenchGuiConfig(
                mcu_options=tuple(mcu_options),
                com_port_options=tuple(com_port_options),
                baud_options=tuple(baud_options),
                log_level_options=tuple(log_level_options),
                default_log_level=default_log_level,
                manual_servo=ManualServoConfig(
                    default_lane=default_lane,
                    default_position_mm=default_position_mm,
                    min_lane=min_lane,
                    max_lane=max_lane,
                    min_position_mm=min_position_mm,
                    max_position_mm=max_position_mm,
                ),
            ),
        )

    @classmethod
    def load_startup(cls, config_path: str | Path) -> "RuntimeConfig":
        path = Path(config_path)
        stat_result = path.stat()
        if stat_result.st_size > MAX_STARTUP_CONFIG_BYTES:
            raise ConfigValidationError(
                f"Startup config exceeds size limit ({MAX_STARTUP_CONFIG_BYTES} bytes)"
            )
        raw_text = path.read_text(encoding="utf-8")
        return cls.from_text(raw_text)

    def apply_live_update(self, updates: dict[str, str]) -> "RuntimeConfig":
        motion_mode = updates.get(MOTION_MODE, self.motion_mode)
        homing_mode = updates.get(HOMING_MODE, self.homing_mode)
        _validate_enum(MOTION_MODE, motion_mode, MOTION_MODE_VALUES)
        _validate_enum(HOMING_MODE, homing_mode, HOMING_MODE_VALUES)
        return RuntimeConfig(
            motion_mode=motion_mode,
            homing_mode=homing_mode,
            frame_source=self.frame_source,
            camera=self.camera,
            transport=self.transport,
            cycle_timing=self.cycle_timing,
            cycle_latency_budget=self.cycle_latency_budget,
            scheduling_guard=self.scheduling_guard,
            timebase_alignment=self.timebase_alignment,
            telemetry_alarm=self.telemetry_alarm,
            scenario_thresholds=self.scenario_thresholds,
            detection=self.detection,
            baseline_run=self.baseline_run,
            bench_gui=self.bench_gui,
        )



def _parse_simple_yaml(raw_text: str) -> dict[str, Any]:
    if "\t" in raw_text:
        raise ConfigValidationError("Startup config must use spaces for indentation")

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    lines = raw_text.splitlines()
    if len(lines) > MAX_STARTUP_CONFIG_LINES:
        raise ConfigValidationError(f"Startup config exceeds line limit ({MAX_STARTUP_CONFIG_LINES})")

    for line_no, raw_line in enumerate(lines, start=1):
        if len(raw_line) > MAX_YAML_LINE_LENGTH:
            raise ConfigValidationError(
                f"Startup config line {line_no} exceeds {MAX_YAML_LINE_LENGTH} characters"
            )
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise ConfigValidationError(f"Invalid indentation at line {line_no}")

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        if len(stack) > MAX_YAML_NESTING_DEPTH:
            raise ConfigValidationError(
                f"Startup config nesting exceeds depth limit ({MAX_YAML_NESTING_DEPTH})"
            )

        parent = stack[-1][1]

        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise ConfigValidationError(f"List item is not under a list key at line {line_no}")
            item_text = stripped[2:].strip()
            if not item_text:
                raise ConfigValidationError(f"List item value missing at line {line_no}")
            parent.append(_parse_scalar(item_text))
            continue

        if ":" not in stripped:
            raise ConfigValidationError(f"Expected key/value at line {line_no}")

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        value_text = raw_value.strip()
        if not key:
            raise ConfigValidationError(f"Missing key at line {line_no}")

        if not isinstance(parent, dict):
            raise ConfigValidationError(f"Mapping entry is not under a map at line {line_no}")

        if key in parent:
            raise ConfigValidationError(f"Duplicate key '{key}' at line {line_no}")

        if not value_text:
            parent[key] = {}
            stack.append((indent, parent[key]))
            continue

        parent[key] = _parse_scalar(value_text)

        if parent[key] == []:
            stack.append((indent, parent[key]))

    if not isinstance(root, dict):
        raise ConfigValidationError("Startup config must be a YAML mapping")
    return root


def _parse_scalar(raw_value: str) -> Any:
    if raw_value == "[]":
        return []
    if raw_value.startswith("[") and raw_value.endswith("]"):
        inner = raw_value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    if raw_value.lower() in {"true", "false"}:
        return raw_value.lower() == "true"
    if (raw_value.startswith('"') and raw_value.endswith('"')) or (raw_value.startswith("'") and raw_value.endswith("'")):
        return raw_value[1:-1]
    try:
        if any(ch in raw_value for ch in (".", "e", "E")):
            return float(raw_value)
        return int(raw_value)
    except ValueError:
        return raw_value

def _required_map(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigValidationError(f"{key} is required and must be a mapping")
    return value


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"{key} is required and must be a non-empty string")
    out = value.strip()
    _validate_text_field(key, out)
    return out


def _optional_bool(payload: dict[str, Any], key: str, fallback: bool) -> bool:
    if key not in payload:
        return fallback
    value = payload[key]
    if not isinstance(value, bool):
        raise ConfigValidationError(f"{key} must be boolean")
    return value


def _optional_str(payload: dict[str, Any], key: str, fallback: str) -> str:
    if key not in payload:
        return fallback
    value = payload[key]
    if not isinstance(value, str):
        raise ConfigValidationError(f"{key} must be a string")
    out = value.strip()
    _validate_text_field(key, out)
    return out


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigValidationError(f"{key} is required and must be an integer")
    return value


def _optional_int(payload: dict[str, Any], key: str, fallback: int) -> int:
    if key not in payload:
        return fallback
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigValidationError(f"{key} must be an integer")
    return value


def _required_float(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ConfigValidationError(f"{key} is required and must be a number")
    out = float(value)
    _validate_finite_number(key, out)
    return out


def _optional_float(payload: dict[str, Any], key: str, fallback: float) -> float:
    if key not in payload:
        return fallback
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ConfigValidationError(f"{key} must be a number")
    out = float(value)
    _validate_finite_number(key, out)
    return out




def _optional_list_of_str(payload: dict[str, Any], key: str, fallback: tuple[str, ...]) -> list[str]:
    if key not in payload:
        return list(fallback)
    value = payload[key]
    if not isinstance(value, list):
        raise ConfigValidationError(f"{key} must be a list")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConfigValidationError(f"{key} entries must be non-empty strings")
        out.append(item.strip())
    return out


def _optional_list_of_int(payload: dict[str, Any], key: str, fallback: tuple[int, ...]) -> list[int]:
    if key not in payload:
        return list(fallback)
    value = payload[key]
    if not isinstance(value, list):
        raise ConfigValidationError(f"{key} must be a list")
    out: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ConfigValidationError(f"{key} entries must be integers")
        out.append(item)
    return out

def _validate_range(field_name: str, value: float, *, min_value: float | None = None, max_value: float | None = None) -> None:
    if min_value is not None and value < min_value:
        raise ConfigValidationError(f"{field_name} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ConfigValidationError(f"{field_name} must be <= {max_value}")


def _validate_enum(field_name: str, value: str, allowed_values: tuple[str, ...]) -> None:
    if value not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ConfigValidationError(f"Unknown {field_name}: {value}. Allowed: {allowed}")


def _validate_finite_number(field_name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ConfigValidationError(f"{field_name} must be finite")


def _validate_text_field(field_name: str, value: str) -> None:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ConfigValidationError(f"{field_name} must not contain control characters")


def _validate_serial_dependency(transport_kind: str) -> None:
    if transport_kind not in {"serial", "esp32"}:
        return
    if importlib.util.find_spec("serial") is not None:
        return
    raise ConfigValidationError(
        f"transport.kind={transport_kind} requires optional dependency 'pyserial'. "
        "Install with: python -m pip install -e .[serial]"
    )
