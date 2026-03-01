from __future__ import annotations

import pytest

from coloursorter.config import ConfigValidationError, RuntimeConfig


def test_startup_config_rejects_unknown_motion_mode() -> None:
    raw_text = "motion_mode: ENCODER\nhoming_mode: SKIP_HOME\n"
    with pytest.raises(ConfigValidationError):
        RuntimeConfig.from_text(raw_text)


def test_startup_config_accepts_canonical_values() -> None:
    raw_text = (
        "motion_mode: FOLLOW_BELT\n"
        "homing_mode: AUTO_HOME\n"
        "bench_transport: serial\n"
        "serial_port: /dev/ttyUSB0\n"
        "serial_baud: 230400\n"
        "serial_timeout_s: 0.25\n"
    )
    config = RuntimeConfig.from_text(raw_text)
    assert config.motion_mode == "FOLLOW_BELT"
    assert config.homing_mode == "AUTO_HOME"
    assert config.bench_transport == "serial"
    assert config.serial_port == "/dev/ttyUSB0"
    assert config.serial_baud == 230400
    assert config.serial_timeout_s == 0.25


def test_live_update_rejects_unknown_homing_mode() -> None:
    config = RuntimeConfig.from_text("motion_mode: MANUAL\nhoming_mode: SKIP_HOME\n")
    with pytest.raises(ConfigValidationError):
        config.apply_live_update({"homing_mode": "DISABLED"})


def test_runtime_config_rejects_invalid_serial_timeout() -> None:
    with pytest.raises(ConfigValidationError, match="serial_timeout_s must be > 0"):
        RuntimeConfig.from_text("serial_timeout_s: 0\n")
