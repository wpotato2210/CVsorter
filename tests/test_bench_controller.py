from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from coloursorter.bench import AckCode, BenchFrame, BenchLogEntry, FaultState
from coloursorter.config import RuntimeConfig
from gui.bench_app.app import BenchMainWindow, QueueState
from gui.bench_app.controller import BenchAppController, ControllerState


class _FakeFrameSource:
    def __init__(self, frames: list[BenchFrame]) -> None:
        self._frames = list(frames)

    def next_frame(self) -> BenchFrame | None:
        if not self._frames:
            return None
        return self._frames.pop(0)

    def release(self) -> None:
        return None


class _FakeRgbFrame:
    def __init__(self, payload: bytes, width: int, height: int) -> None:
        self._payload = payload
        self.shape = (height, width, 3)

    def tobytes(self) -> bytes:
        return self._payload


class _RecordingRunner:
    def __init__(self, logs: tuple[BenchLogEntry, ...]) -> None:
        self.logs = logs
        self.calls: list[dict[str, float | int]] = []

    def run_cycle(self, **kwargs):
        self.calls.append(kwargs)
        return self.logs


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def runtime_config() -> RuntimeConfig:
    return RuntimeConfig.load_startup(Path(__file__).resolve().parents[1] / "configs" / "bench_runtime.yaml")


def test_controller_state_transitions_idle_replay_live_fault(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    assert controller.runtime_state.controller_state == ControllerState.IDLE

    controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")
    assert controller.runtime_state.controller_state == ControllerState.REPLAY_RUNNING
    assert not controller.window.replay_button.isEnabled()

    # Illegal transition is ignored.
    controller._transition_to(ControllerState.LIVE_RUNNING)
    assert controller.runtime_state.controller_state == ControllerState.REPLAY_RUNNING

    controller._transition_to(ControllerState.FAULTED, overlay_text="Watchdog fault active")
    assert controller.runtime_state.controller_state == ControllerState.FAULTED

    controller._transition_to(ControllerState.IDLE)
    assert controller.runtime_state.controller_state == ControllerState.IDLE

    controller._transition_to(ControllerState.LIVE_RUNNING, overlay_text="Live mode active")
    assert controller.runtime_state.controller_state == ControllerState.LIVE_RUNNING


def test_cycle_processing_is_deterministic_with_mocked_frame_source_and_clock(
    qapp: QApplication, runtime_config: RuntimeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = BenchAppController(qapp, runtime_config)
    expected_log = BenchLogEntry(
        frame_timestamp_s=0.250,
        trigger_generation_s=0.200,
        lane=2,
        decision="reject",
        rejection_reason="classified_reject",
        protocol_round_trip_ms=6.4,
        ack_code=AckCode.ACK,
    )
    recording_runner = _RecordingRunner((expected_log,))
    controller.bench_runner = recording_runner

    frame = BenchFrame(frame_id=7, timestamp_s=0.250, image_bgr=object())
    controller._frame_source = _FakeFrameSource([frame])
    controller.runtime_state.previous_timestamp_s = 0.200
    controller.runtime_state.controller_state = ControllerState.REPLAY_RUNNING

    monkeypatch.setattr("gui.bench_app.controller.cv2.cvtColor", lambda _image, _code: _FakeRgbFrame(b"abc", 2, 2))

    observed_logs: list[BenchLogEntry] = []
    controller.log_entry_requested.connect(lambda entry: observed_logs.append(entry))

    controller._on_cycle_tick()

    assert len(recording_runner.calls) == 1
    assert recording_runner.calls[0]["frame_id"] == 7
    assert recording_runner.calls[0]["timestamp_s"] == pytest.approx(0.250)
    assert recording_runner.calls[0]["previous_timestamp_s"] == pytest.approx(0.200)
    assert observed_logs == [expected_log]
    assert controller.runtime_state.previous_timestamp_s == pytest.approx(0.250)


def test_ui_update_side_effects_log_queue_fault_labels(qapp: QApplication) -> None:
    window = BenchMainWindow()

    window.set_queue_state(QueueState(depth=3, capacity=8, state="replay_running"))
    assert window.queue_depth_label.text() == "Depth: 3/8"
    assert window.queue_state_label.text() == "State: replay_running"

    window.set_fault_state(FaultState.SAFE)
    assert window.safe_label.text() == "SAFE: on"
    assert window.watchdog_label.text() == "WATCHDOG: off"

    first = BenchLogEntry(0.1, 0.1, 1, "accept", None, 4.2, AckCode.ACK)
    second = BenchLogEntry(0.2, 0.2, 2, "reject", "classified_reject", 5.3, AckCode.NACK_QUEUE_FULL)
    window.append_log_entry(first)
    window.append_log_entry(second)

    assert window.log_table.rowCount() == 2
    assert window.log_table.item(1, 2).text() == "2/reject"
    assert window.log_table.item(1, 5).text() == "NACK_QUEUE_FULL"
