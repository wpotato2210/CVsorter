from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


from coloursorter.config.enums import (
    HOMING_MODE,
    HOMING_MODE_VALUES,
    MOTION_MODE,
    MOTION_MODE_VALUES,
)


class ConfigValidationError(ValueError):
    pass


FRAME_SOURCE_VALUES = ("replay", "live")
BENCH_TRANSPORT_VALUES = ("mock", "serial")
QUEUE_CONSUMPTION_VALUES = ("none", "one_per_tick", "all")

DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
DEFAULT_SERIAL_BAUD = 115200
DEFAULT_SERIAL_TIMEOUT_S = 0.100


@dataclass(frozen=True)
class FrameSourceConfig:
    mode: str
    replay_path: str
    replay_frame_period_s: float


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
class ScenarioThresholdsConfig:
    nominal_max_avg_rtt_ms: float
    nominal_max_peak_rtt_ms: float
    stress_max_avg_rtt_ms: float
    stress_max_peak_rtt_ms: float
    fault_max_avg_rtt_ms: float
    fault_max_peak_rtt_ms: float


@dataclass(frozen=True)
class RuntimeConfig:
    motion_mode: str
    homing_mode: str
    frame_source: FrameSourceConfig
    camera: CameraConfig
    transport: TransportConfig
    cycle_timing: CycleTimingConfig
    scenario_thresholds: ScenarioThresholdsConfig

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

        cycle_payload = _required_map(payload, "cycle_timing")
        period_ms = _required_int(cycle_payload, "period_ms")
        queue_consumption_policy = _required_str(cycle_payload, "queue_consumption_policy")
        _validate_range("cycle_timing.period_ms", period_ms, min_value=1)
        _validate_enum("cycle_timing.queue_consumption_policy", queue_consumption_policy, QUEUE_CONSUMPTION_VALUES)

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

        return cls(
            motion_mode=motion_mode,
            homing_mode=homing_mode,
            frame_source=FrameSourceConfig(
                mode=frame_mode,
                replay_path=replay_path,
                replay_frame_period_s=replay_frame_period_s,
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
            scenario_thresholds=scenario_thresholds,
        )

    @classmethod
    def load_startup(cls, config_path: str | Path) -> "RuntimeConfig":
        raw_text = Path(config_path).read_text(encoding="utf-8")
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
            scenario_thresholds=self.scenario_thresholds,
        )



def _parse_simple_yaml(raw_text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_no, raw_line in enumerate(raw_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise ConfigValidationError(f"Invalid indentation at line {line_no}")
        if ":" not in stripped:
            raise ConfigValidationError(f"Expected key/value at line {line_no}")

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        value_text = raw_value.strip()
        if not key:
            raise ConfigValidationError(f"Missing key at line {line_no}")

        if not value_text:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
            continue

        parent[key] = _parse_scalar(value_text)

    if not isinstance(root, dict):
        raise ConfigValidationError("Startup config must be a YAML mapping")
    return root


def _parse_scalar(raw_value: str) -> Any:
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
    return value.strip()


def _optional_str(payload: dict[str, Any], key: str, fallback: str) -> str:
    if key not in payload:
        return fallback
    value = payload[key]
    if not isinstance(value, str):
        raise ConfigValidationError(f"{key} must be a string")
    return value.strip()


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
    return float(value)


def _optional_float(payload: dict[str, Any], key: str, fallback: float) -> float:
    if key not in payload:
        return fallback
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ConfigValidationError(f"{key} must be a number")
    return float(value)


def _validate_range(field_name: str, value: float, *, min_value: float | None = None, max_value: float | None = None) -> None:
    if min_value is not None and value < min_value:
        raise ConfigValidationError(f"{field_name} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ConfigValidationError(f"{field_name} must be <= {max_value}")


def _validate_enum(field_name: str, value: str, allowed_values: tuple[str, ...]) -> None:
    if value not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ConfigValidationError(f"Unknown {field_name}: {value}. Allowed: {allowed}")
