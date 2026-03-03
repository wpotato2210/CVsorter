from __future__ import annotations

import importlib.util

import pytest

from coloursorter.config import ConfigValidationError, RuntimeConfig


@pytest.fixture(autouse=True)
def _serial_dependency_available_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    original_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "serial" else original_find_spec(name),
    )


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
cycle_latency_budget:
  ingest_ms: 4.0
  detect_ms: 8.0
  decide_ms: 8.0
  send_ms: 5.0
  total_ms: 25.0
scheduling_guard:
  max_queue_age_ms: 20.0
  max_frame_staleness_ms: 50.0
timebase_alignment:
  strategy: encoder_epoch
  host_to_mcu_offset_ms: 0.0
telemetry_alarm:
  jitter_warn_ms: 5.0
  jitter_critical_ms: 10.0
scenario_thresholds:
  nominal_max_avg_rtt_ms: 12.0
  nominal_max_peak_rtt_ms: 25.0
  stress_max_avg_rtt_ms: 25.0
  stress_max_peak_rtt_ms: 60.0
  fault_max_avg_rtt_ms: 40.0
  fault_max_peak_rtt_ms: 80.0
detection:
  provider: opencv_basic
  opencv_basic:
    min_area_px: 120
    reject_red_threshold: 140
  opencv_calibrated:
    min_area_px: 120
    reject_hue_min: 0
    reject_hue_max: 12
    reject_saturation_min: 90
    reject_value_min: 90

  model_stub:
    reject_threshold: 0.5
baseline_run:
  detector_threshold: 0.5
  calibration_mode: fixed
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
    assert config.detection.provider == "opencv_basic"
    assert config.baseline_run.calibration_mode == "fixed"
    assert config.detection.active_camera_recipe == "default"
    assert config.detection.active_lighting_recipe == "default"
    assert config.detection.preprocess.enable_normalization is True
    assert config.cycle_latency_budget.total_ms == 25.0
    assert config.timebase_alignment.strategy == "encoder_epoch"


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


def test_runtime_config_rejects_unknown_detection_provider() -> None:
    raw_text = _canonical_text().replace("provider: opencv_basic", "provider: unknown")
    with pytest.raises(ConfigValidationError, match="Unknown detection.provider"):
        RuntimeConfig.from_text(raw_text)


def test_runtime_config_serial_mode_requires_optional_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    original_find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None if name == "serial" else original_find_spec(name))
    with pytest.raises(ConfigValidationError, match="Install with: python -m pip install -e .\\[serial\\]"):
        RuntimeConfig.from_text(_canonical_text())


def test_runtime_config_accepts_esp32_transport_kind() -> None:
    raw_text = _canonical_text().replace("kind: serial", "kind: esp32", 1)

    config = RuntimeConfig.from_text(raw_text)

    assert config.transport.kind == "esp32"


@pytest.mark.parametrize(
    ("field_path", "value", "error_field"),
    [
        (("frame_source", "replay_frame_period_s"), float("nan"), "replay_frame_period_s"),
        (("transport", "base_round_trip_ms"), float("inf"), "base_round_trip_ms"),
        (("baseline_run", "detector_threshold"), float("-inf"), "detector_threshold"),
    ],
)
def test_runtime_config_rejects_non_finite_numbers(field_path: tuple[str, str], value: float, error_field: str) -> None:
    from coloursorter.config.runtime import _parse_simple_yaml

    payload = _parse_simple_yaml(_canonical_text())
    payload[field_path[0]][field_path[1]] = value
    with pytest.raises(ConfigValidationError, match=f"{error_field} must be finite"):
        RuntimeConfig.from_dict(payload)


def test_runtime_config_esp32_mode_requires_optional_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    original_find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None if name == "serial" else original_find_spec(name))

    raw_text = _canonical_text().replace("kind: serial", "kind: esp32", 1)
    with pytest.raises(ConfigValidationError, match="transport.kind=esp32 requires optional dependency"):
        RuntimeConfig.from_text(raw_text)


def test_runtime_config_uses_profiled_detection_thresholds() -> None:
    from coloursorter.config.runtime import _parse_simple_yaml

    payload = _parse_simple_yaml(_canonical_text())
    payload["detection"]["active_camera_recipe"] = "cam_a"
    payload["detection"]["active_lighting_recipe"] = "bright"
    payload["detection"]["profiles"] = [
        {
            "camera_recipe": "cam_a",
            "lighting_recipe": "bright",
            "opencv_basic": {"min_area_px": 80, "reject_red_threshold": 170},
            "opencv_calibrated": {
                "min_area_px": 110,
                "reject_hue_min": 0,
                "reject_hue_max": 15,
                "reject_saturation_min": 95,
                "reject_value_min": 95,
            },
            "model_stub": {"reject_threshold": 0.7},
        }
    ]
    config = RuntimeConfig.from_dict(payload)
    profile = config.detection.profiles[0]
    assert profile.camera_recipe == "cam_a"
    assert profile.lighting_recipe == "bright"
    assert profile.opencv_basic.reject_red_threshold == 170
