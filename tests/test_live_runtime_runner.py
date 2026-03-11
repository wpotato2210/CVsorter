from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from coloursorter.bench.types import BenchFrame
from coloursorter.model import ObjectDetection
from coloursorter.runtime.live_runner import LiveRuntimeRunner

_RUNTIME_TEMPLATE = """
motion_mode: FOLLOW_BELT
homing_mode: SKIP_HOME

frame_source:
  mode: {mode}
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
class _FakeFrameSource:
    _frame: BenchFrame | None = None

    def open(self) -> None:
        self._frame = BenchFrame(frame_id=0, timestamp_s=0.0, image_bgr=np.zeros((240, 1100, 3), dtype=np.uint8))

    def next_frame(self) -> BenchFrame | None:
        frame = self._frame
        self._frame = None
        return frame

    def release(self) -> None:
        return


class _FakeDetector:
    provider_version = "provider-v1"
    model_version = "model-v1"
    active_config_hash = "cfg-hash-v1"

    def detect(self, _image_bgr: object) -> list[ObjectDetection]:
        return [
            ObjectDetection(
                object_id="det-1",
                centroid_x_px=20.0,
                centroid_y_px=20.0,
                classification="reject",
                infection_score=1.0,
            )
        ]


class _FakeTransport:
    def __init__(self) -> None:
        self.sent = 0
        self.closed = False

    def send(self, _command):
        self.sent += 1

    def send_command(self, _command, _args=()):
        return None

    def close(self):
        self.closed = True


def _write_runtime_config(tmp_path: Path, mode: str) -> Path:
    path = tmp_path / "runtime.yaml"
    path.write_text(_RUNTIME_TEMPLATE.format(mode=mode), encoding="utf-8")
    return path


def test_live_runner_executes_loop_and_sends_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_path = _write_runtime_config(tmp_path, mode="live")
    transport = _FakeTransport()

    monkeypatch.setattr("coloursorter.runtime.live_runner.LiveFrameSource", lambda _cfg: _FakeFrameSource())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_detection_provider", lambda _cfg: _FakeDetector())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_transport", lambda _cfg: transport)

    runner = LiveRuntimeRunner(runtime_config_path=runtime_path)
    result = runner.run(max_cycles=1, enable_reporting=False)

    assert result.cycle_count == 1
    assert result.sent_command_count == 1
    assert result.reports == ()
    assert transport.sent == 1
    assert transport.closed


def test_live_runner_reporting_is_optional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_path = _write_runtime_config(tmp_path, mode="live")
    transport = _FakeTransport()
    emitted: list[int] = []

    monkeypatch.setattr("coloursorter.runtime.live_runner.LiveFrameSource", lambda _cfg: _FakeFrameSource())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_detection_provider", lambda _cfg: _FakeDetector())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_transport", lambda _cfg: transport)

    runner = LiveRuntimeRunner(runtime_config_path=runtime_path)
    result = runner.run(max_cycles=1, enable_reporting=True, report_callback=lambda report: emitted.append(report.frame_id))

    assert len(result.reports) == 1
    assert emitted == [0]
    report = result.reports[0]
    assert report.canonical_timing == report.timing
    assert report.frame_timestamp_ms == report.timing.frame_timestamp_ms
    assert report.pipeline_latency_ms == report.timing.pipeline_latency_ms
    assert report.trigger_offset_ms == report.timing.trigger_offset_ms
    assert report.actuation_delay_ms == report.timing.actuation_delay_ms


def test_live_runner_startup_diagnostics_report_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_path = _write_runtime_config(tmp_path, mode="live")

    monkeypatch.setattr("coloursorter.runtime.live_runner.LiveFrameSource", lambda _cfg: _FakeFrameSource())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_detection_provider", lambda _cfg: _FakeDetector())
    monkeypatch.setattr("coloursorter.runtime.live_runner.build_live_transport", lambda _cfg: _FakeTransport())

    runner = LiveRuntimeRunner(runtime_config_path=runtime_path)

    assert runner.startup_diagnostics.all_passed
    assert runner.startup_diagnostics.frame_source_frame.passed
    assert runner.startup_diagnostics.detector_metadata.passed
    assert runner.startup_diagnostics.transport_ping.passed


def test_live_runner_requires_live_mode(tmp_path: Path) -> None:
    runtime_path = _write_runtime_config(tmp_path, mode="replay")
    with pytest.raises(ValueError, match="frame_source.mode=live"):
        LiveRuntimeRunner(runtime_config_path=runtime_path)
