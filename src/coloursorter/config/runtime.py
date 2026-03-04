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


@dataclass(frozen=True)
class RuntimeConfig:
    motion_mode: str
    homing_mode: str

    @classmethod
    def from_text(cls, raw_text: str) -> "RuntimeConfig":
        motion_mode = _extract_scalar(raw_text, MOTION_MODE, DEFAULT_MOTION_MODE)
        homing_mode = _extract_scalar(raw_text, HOMING_MODE, DEFAULT_HOMING_MODE)
        _validate_enum(MOTION_MODE, motion_mode, MOTION_MODE_VALUES)
        _validate_enum(HOMING_MODE, homing_mode, HOMING_MODE_VALUES)
        return cls(motion_mode=motion_mode, homing_mode=homing_mode)

    @classmethod
    def load_startup(cls, config_path: str | Path) -> "RuntimeConfig":
        raw_text = Path(config_path).read_text(encoding="utf-8")
        return cls.from_text(raw_text)

    def apply_live_update(self, updates: dict[str, str]) -> "RuntimeConfig":
        unknown_keys = sorted(set(updates) - {MOTION_MODE, HOMING_MODE})
        if unknown_keys:
            names = ", ".join(unknown_keys)
            raise ConfigValidationError(f"Unknown live update field(s): {names}")

        motion_mode = updates.get(MOTION_MODE, self.motion_mode)
        homing_mode = updates.get(HOMING_MODE, self.homing_mode)
        _validate_enum(MOTION_MODE, motion_mode, MOTION_MODE_VALUES)
        _validate_enum(HOMING_MODE, homing_mode, HOMING_MODE_VALUES)
        return RuntimeConfig(motion_mode=motion_mode, homing_mode=homing_mode)


def _extract_scalar(raw_text: str, key: str, fallback: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", raw_text, re.MULTILINE)
    if not match:
        return fallback
    return match.group(1).strip()


def _validate_enum(field_name: str, value: str, allowed_values: tuple[str, ...]) -> None:
    if value not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ConfigValidationError(f"Unknown {field_name}: {value}. Allowed: {allowed}")
