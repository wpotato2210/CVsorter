from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from coloursorter.bench.types import BenchFrame
from coloursorter.config.runtime import ConfigValidationError
from coloursorter.runtime.live_runner import LiveRuntimeRunner

_RUNTIME_TEMPLATE = """
motion_mode: FOLLOW_BELT
homing_mode: SKIP_HOME

frame_source:
  mode: live
  replay_path: data
  replay_frame_period_s: 0.033333333

camera:
  index: 0
  frame_period_s: 0.033333333

transport:
  kind: mock
  max_queue_depth: 8
  base_round_trip_ms: 2.0
  per_item_penalty_ms: 0.8
  serial:
    port: /dev/ttyACM0
    baud: 115200
    timeout_s: 0.1

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
  nominal_max_avg_rtt_ms: 10.0
  nominal_max_peak_rtt_ms: 20.0
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

bench_gui:
  serial_options:
    mcu_options: [mock, serial, esp32]
    com_port_options: [/dev/ttyACM0, /dev/ttyUSB0, COM3]
    baud_options: [9600, 57600, 115200, 230400]
  logging:
    levels: [DEBUG, INFO, WARN, ERROR]
    default_level: INFO
  manual_servo:
    min_lane: 0
    max_lane: 7
    default_lane: 0
    min_position_mm: 0.0
    max_position_mm: 1000.0
    default_position_mm: 100.0
"""


@dataclass
class _FrameSourceSingleInvalid:
    def open(self) -> None:
        return None

    def next_frame(self) -> BenchFrame:
        return BenchFrame(frame_id=0, timestamp_s=0.0, image_bgr=np.zeros((4, 4), dtype=np.uint8))

    def release(self) -> None:
        return None


class _DetectorMissingMetadata:
    provider_version = ""
    model_version = ""
    active_config_hash = ""

    def detect(self, _image_bgr: object) -> list[object]:
        return []


class _FailPingTransport:
    def send_command(self, _command, _args=()):
        raise RuntimeError("transport offline")

    def close(self):
        return None


def _write_runtime_config(tmp_path: Path, *, text: str = _RUNTIME_TEMPLATE) -> Path:
    path = tmp_path / "runtime.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_runtime_startup_gate_blocks_on_diagnostics_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_path = _write_runtime_config(tmp_path)
    failure_sink_payloads: list[dict[str, str]] = []

    monkeypatch.setattr("coloursorter.runtime.live_runner.LiveFrameSource", lambda _cfg: _FrameSourceSingleInvalid())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_detection_provider", lambda _cfg: _DetectorMissingMetadata())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_transport", lambda _cfg: _FailPingTransport())

    runner = LiveRuntimeRunner(runtime_config_path=runtime_path, failure_sink=failure_sink_payloads.append)
    result = runner.run(max_cycles=1, enable_reporting=False)

    assert result.startup_failed is True
    assert result.cycle_count == 0
    assert result.startup_failure_payload == {
        "status": "startup_failed",
        "config_and_profile": "runtime_config_loaded profile_resolved",
        "detector_metadata": "missing_detector_metadata=provider_version,model_version,active_config_hash",
        "frame_source_frame": "invalid_frame_shape=(4, 4) expected=(H,W,3)_bgr",
        "transport_ping": "transport_ping_error=transport offline",
    }
    assert failure_sink_payloads == [result.startup_failure_payload]


def test_runtime_init_rejects_invalid_configuration_deterministically(tmp_path: Path) -> None:
    invalid = _RUNTIME_TEMPLATE.replace("kind: mock", "kind: unsupported")
    runtime_path = _write_runtime_config(tmp_path, text=invalid)

    with pytest.raises(ConfigValidationError, match="transport.kind"):
        LiveRuntimeRunner(runtime_config_path=runtime_path)


def test_runtime_loop_never_executes_when_startup_gate_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_path = _write_runtime_config(tmp_path)

    class _NoFrameSource:
        def open(self) -> None:
            return None

        def next_frame(self):
            return None

        def release(self) -> None:
            return None

    class _TrapDetector(_DetectorMissingMetadata):
        provider_version = "provider"
        model_version = "model"
        active_config_hash = "hash"

        def detect(self, _image_bgr: object) -> list[object]:
            raise AssertionError("loop body should not run when startup diagnostics fail")

    monkeypatch.setattr("coloursorter.runtime.live_runner.LiveFrameSource", lambda _cfg: _NoFrameSource())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_detection_provider", lambda _cfg: _TrapDetector())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_transport", lambda _cfg: _FailPingTransport())

    runner = LiveRuntimeRunner(runtime_config_path=runtime_path)
    result = runner.run(max_cycles=5, enable_reporting=False)

    assert result.startup_failed is True
    assert result.cycle_count == 0
    assert result.sent_command_count == 0
