from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from coloursorter.config.enums import (
    DEFAULT_HOMING_MODE,
    DEFAULT_MOTION_MODE,
    HOMING_MODE,
    HOMING_MODE_VALUES,
    MOTION_MODE,
    MOTION_MODE_VALUES,
)


class ConfigValidationError(ValueError):
    pass


DEFAULT_BENCH_TRANSPORT = "mock"
BENCH_TRANSPORT_VALUES = ("mock", "serial")
DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
DEFAULT_SERIAL_BAUD = 115200
DEFAULT_SERIAL_TIMEOUT_S = 0.100


@dataclass(frozen=True)
class RuntimeConfig:
    motion_mode: str
    homing_mode: str
    bench_transport: str
    serial_port: str
    serial_baud: int
    serial_timeout_s: float

    @classmethod
    def from_text(cls, raw_text: str) -> "RuntimeConfig":
        motion_mode = _extract_scalar(raw_text, MOTION_MODE, DEFAULT_MOTION_MODE)
        homing_mode = _extract_scalar(raw_text, HOMING_MODE, DEFAULT_HOMING_MODE)
        bench_transport = _extract_scalar(raw_text, "bench_transport", DEFAULT_BENCH_TRANSPORT)
        serial_port = _extract_scalar(raw_text, "serial_port", DEFAULT_SERIAL_PORT)
        serial_baud = _extract_int(raw_text, "serial_baud", DEFAULT_SERIAL_BAUD)
        serial_timeout_s = _extract_float(raw_text, "serial_timeout_s", DEFAULT_SERIAL_TIMEOUT_S)

        _validate_enum(MOTION_MODE, motion_mode, MOTION_MODE_VALUES)
        _validate_enum(HOMING_MODE, homing_mode, HOMING_MODE_VALUES)
        _validate_enum("bench_transport", bench_transport, BENCH_TRANSPORT_VALUES)
        if serial_baud <= 0:
            raise ConfigValidationError("serial_baud must be > 0")
        if serial_timeout_s <= 0:
            raise ConfigValidationError("serial_timeout_s must be > 0")

        return cls(
            motion_mode=motion_mode,
            homing_mode=homing_mode,
            bench_transport=bench_transport,
            serial_port=serial_port,
            serial_baud=serial_baud,
            serial_timeout_s=serial_timeout_s,
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
            bench_transport=self.bench_transport,
            serial_port=self.serial_port,
            serial_baud=self.serial_baud,
            serial_timeout_s=self.serial_timeout_s,
        )


def _extract_scalar(raw_text: str, key: str, fallback: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", raw_text, re.MULTILINE)
    if not match:
        return fallback
    return match.group(1).strip()


def _extract_int(raw_text: str, key: str, fallback: int) -> int:
    value = _extract_scalar(raw_text, key, str(fallback))
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigValidationError(f"{key} must be an integer") from exc


def _extract_float(raw_text: str, key: str, fallback: float) -> float:
    value = _extract_scalar(raw_text, key, str(fallback))
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigValidationError(f"{key} must be a number") from exc


def _validate_enum(field_name: str, value: str, allowed_values: tuple[str, ...]) -> None:
    if value not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ConfigValidationError(f"Unknown {field_name}: {value}. Allowed: {allowed}")
