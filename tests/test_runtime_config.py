from __future__ import annotations

import pytest

from coloursorter.config import ConfigValidationError, RuntimeConfig


def test_startup_config_rejects_unknown_motion_mode() -> None:
    raw_text = "motion_mode: ENCODER\nhoming_mode: SKIP_HOME\n"
    with pytest.raises(ConfigValidationError):
        RuntimeConfig.from_text(raw_text)


def test_startup_config_accepts_canonical_values() -> None:
    raw_text = "motion_mode: FOLLOW_BELT\nhoming_mode: AUTO_HOME\n"
    config = RuntimeConfig.from_text(raw_text)
    assert config.motion_mode == "FOLLOW_BELT"
    assert config.homing_mode == "AUTO_HOME"


def test_live_update_rejects_unknown_homing_mode() -> None:
    config = RuntimeConfig.from_text("motion_mode: MANUAL\nhoming_mode: SKIP_HOME\n")
    with pytest.raises(ConfigValidationError):
        config.apply_live_update({"homing_mode": "DISABLED"})
