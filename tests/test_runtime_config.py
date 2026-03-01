from __future__ import annotations

import pytest

from coloursorter.config import ConfigValidationError, RuntimeConfig


def _canonical_text() -> str:
    return """
motion_mode: FOLLOW_BELT
homing_mode: AUTO_HOME
frame_source:
  mode: replay
  replay_path: data
  replay_frame_period_s: 0.033
camera:
  index: 0
  frame_period_s: 0.033
transport:
  kind: serial
  max_queue_depth: 8
  base_round_trip_ms: 2.0
  per_item_penalty_ms: 0.8
  serial:
    port: /dev/ttyUSB0
    baud: 230400
    timeout_s: 0.25
cycle_timing:
  period_ms: 33
  queue_consumption_policy: one_per_tick
scenario_thresholds:
  nominal_max_avg_rtt_ms: 12.0
  nominal_max_peak_rtt_ms: 25.0
  stress_max_avg_rtt_ms: 25.0
  stress_max_peak_rtt_ms: 60.0
  fault_max_avg_rtt_ms: 40.0
  fault_max_peak_rtt_ms: 80.0
"""


def test_startup_config_rejects_unknown_motion_mode() -> None:
    raw_text = _canonical_text().replace("FOLLOW_BELT", "ENCODER", 1)
    with pytest.raises(ConfigValidationError):
        RuntimeConfig.from_text(raw_text)


def test_startup_config_accepts_canonical_values() -> None:
    config = RuntimeConfig.from_text(_canonical_text())
    assert config.motion_mode == "FOLLOW_BELT"
    assert config.homing_mode == "AUTO_HOME"
    assert config.transport.kind == "serial"
    assert config.transport.serial_port == "/dev/ttyUSB0"
    assert config.transport.serial_baud == 230400
    assert config.transport.serial_timeout_s == 0.25


def test_live_update_rejects_unknown_homing_mode() -> None:
    config = RuntimeConfig.from_text(_canonical_text())
    with pytest.raises(ConfigValidationError):
        config.apply_live_update({"homing_mode": "DISABLED"})


def test_runtime_config_rejects_invalid_serial_timeout() -> None:
    raw_text = _canonical_text().replace("timeout_s: 0.25", "timeout_s: 0")
    with pytest.raises(ConfigValidationError, match="transport.serial.timeout_s must be >= 0.001"):
        RuntimeConfig.from_text(raw_text)


def test_runtime_config_requires_nested_sections() -> None:
    with pytest.raises(ConfigValidationError, match="frame_source is required"):
        RuntimeConfig.from_text("motion_mode: FOLLOW_BELT\nhoming_mode: SKIP_HOME\n")
