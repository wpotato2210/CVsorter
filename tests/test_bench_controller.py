from __future__ import annotations

import os
from pathlib import Path
from dataclasses import replace

import pytest

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - environment dependent
    pytest.skip("PySide6 with system GL dependencies is required for GUI tests", allow_module_level=True)

from coloursorter.bench import AckCode, BenchFrame, BenchLogEntry, FaultState
from coloursorter.bench.types import TransportResponse
from coloursorter.scheduler import ScheduledCommand
from coloursorter.config import RuntimeConfig
from gui.bench_app.app import BenchMainWindow, QueueState
from gui.bench_app.controller import BenchAppController, ControllerState, OperatorMode


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
        self.calls: list[dict[str, object]] = []

    def process_ingest_payload(self, payload: dict[str, object]):
        self.calls.append(payload)
        return self.logs


class _StubSerialTransport:
    def __init__(self, *_args, **_kwargs) -> None:
        self._fault_state = FaultState.NORMAL
        self._queue_depth = 0
        self._last_queue_cleared = False

    def send(self, _command: ScheduledCommand) -> TransportResponse:
        self._queue_depth = 2
        self._last_queue_cleared = False
        return TransportResponse(
            ack_code=AckCode.ACK,
            queue_depth=2,
            round_trip_ms=4.0,
            fault_state=FaultState.NORMAL,
            scheduler_state="ACTIVE",
            mode="AUTO",
            queue_cleared=False,
        )

    def current_fault_state(self) -> FaultState:
        return self._fault_state

    def current_queue_depth(self) -> int:
        return self._queue_depth

    def transport_queue_depth(self) -> int:
        return self._queue_depth

    def last_queue_cleared_observation(self) -> bool:
        return self._last_queue_cleared

    def transport_last_queue_cleared(self) -> bool:
        return self._last_queue_cleared

    def close(self) -> None:
        return None


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
    assert recording_runner.calls[0]["timestamp"] == pytest.approx(0.250)
    assert recording_runner.calls[0]["previous_timestamp_s"] == pytest.approx(0.200)
    assert observed_logs == [expected_log]
    assert controller.runtime_state.previous_timestamp_s == pytest.approx(0.250)


def test_ui_update_side_effects_log_queue_fault_labels(qapp: QApplication) -> None:
    window = BenchMainWindow()

    window.set_queue_state(QueueState(depth=3, capacity=8, controller_state="replay_running", scheduler_state="ACTIVE", mode="AUTO"))
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


class _RecordingDetector:
    def __init__(self, detections) -> None:
        self._detections = detections
        self.calls = 0

    def detect(self, _frame_bgr):
        self.calls += 1
        return self._detections


def test_controller_cycle_uses_detector_output_for_runner(
    qapp: QApplication, runtime_config: RuntimeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = BenchAppController(qapp, runtime_config)
    detections = [
        {
            "object_id": "det-1",
            "centroid_x_px": 10.0,
            "centroid_y_px": 10.0,
            "classification": "reject",
        }
    ]
    from coloursorter.model import ObjectDetection

    detector = _RecordingDetector([ObjectDetection(**detections[0])])
    controller._detector = detector

    recording_runner = _RecordingRunner(())
    controller.bench_runner = recording_runner

    frame = BenchFrame(frame_id=1, timestamp_s=0.1, image_bgr=object())
    controller._frame_source = _FakeFrameSource([frame])
    controller.runtime_state.previous_timestamp_s = 0.0
    controller.runtime_state.controller_state = ControllerState.REPLAY_RUNNING

    monkeypatch.setattr("gui.bench_app.controller.cv2.cvtColor", lambda _image, _code: _FakeRgbFrame(b"abc", 2, 2))

    controller._on_cycle_tick()

    assert detector.calls == 1
    assert len(recording_runner.calls) == 1
    assert len(recording_runner.calls[0]["detections"]) == 1
    assert recording_runner.calls[0]["detections"][0].object_id == "det-1"


def test_safe_state_home_recovery_transitions_to_manual_only(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller.runtime_state.fault_state = FaultState.SAFE
    controller._set_operator_mode(OperatorMode.SAFE)
    controller._set_protocol_mode(OperatorMode.SAFE)
    controller._transition_to(ControllerState.SAFE, overlay_text="SAFE fault active")

    controller.on_home_clicked()

    assert controller.runtime_state.controller_state == ControllerState.IDLE
    assert controller.runtime_state.fault_state == FaultState.NORMAL
    assert controller.runtime_state.operator_mode == OperatorMode.MANUAL


def test_serial_connect_error_detail_maps_missing_pyserial_message(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)
    detail = controller._serial_connect_error_detail(RuntimeError("pyserial is required for SerialMcuTransport"))
    assert detail == "pyserial missing; install with: python -m pip install -e .[serial]"


def test_safe_state_can_recover_manual_then_auto(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller.runtime_state.fault_state = FaultState.SAFE
    controller._set_operator_mode(OperatorMode.SAFE)
    controller._set_protocol_mode(OperatorMode.SAFE)
    controller._transition_to(ControllerState.SAFE, overlay_text="SAFE fault active")

    assert controller.recover_safe_to_manual() is True
    assert controller.runtime_state.controller_state == ControllerState.IDLE
    assert controller.runtime_state.operator_mode == OperatorMode.MANUAL

    assert controller.recover_to_auto() is True
    assert controller.runtime_state.operator_mode == OperatorMode.AUTO


def test_safe_recovery_calls_are_rejected_when_not_in_safe(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    assert controller.recover_safe_to_manual() is False


def test_safe_to_auto_transition_is_rejected_by_controller_policy(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller.runtime_state.fault_state = FaultState.SAFE
    controller._set_operator_mode(OperatorMode.SAFE)
    controller._set_protocol_mode(OperatorMode.SAFE)
    controller._transition_to(ControllerState.SAFE, overlay_text="SAFE fault active")

    assert controller.recover_to_auto() is False
    assert controller.runtime_state.controller_state == ControllerState.SAFE
    assert controller.runtime_state.operator_mode == OperatorMode.SAFE


def test_recover_to_auto_requires_idle_controller_state(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller._set_operator_mode(OperatorMode.MANUAL)
    controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")

    assert controller.recover_to_auto() is False
    assert controller.runtime_state.operator_mode == OperatorMode.MANUAL

    controller._transition_to(ControllerState.IDLE)
    assert controller.recover_to_auto() is True
    assert controller.runtime_state.operator_mode == OperatorMode.AUTO


def test_mode_changed_signal_updates_home_button_label(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller._set_operator_mode(OperatorMode.SAFE)
    assert controller.window.home_button.text() == "Clear SAFE"

    controller._set_operator_mode(OperatorMode.MANUAL)
    assert controller.window.home_button.text() == "Home"




@pytest.mark.parametrize(
    ("current_mode", "target_mode", "expected_allowed"),
    [
        (OperatorMode.AUTO, OperatorMode.AUTO, True),
        (OperatorMode.AUTO, OperatorMode.MANUAL, True),
        (OperatorMode.AUTO, OperatorMode.SAFE, True),
        (OperatorMode.MANUAL, OperatorMode.AUTO, True),
        (OperatorMode.MANUAL, OperatorMode.MANUAL, True),
        (OperatorMode.MANUAL, OperatorMode.SAFE, True),
        (OperatorMode.SAFE, OperatorMode.AUTO, False),
        (OperatorMode.SAFE, OperatorMode.MANUAL, True),
        (OperatorMode.SAFE, OperatorMode.SAFE, True),
    ],
)
def test_controller_mode_transition_outcomes_match_protocol_contract(
    qapp: QApplication,
    runtime_config: RuntimeConfig,
    current_mode: OperatorMode,
    target_mode: OperatorMode,
    expected_allowed: bool,
) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller._set_operator_mode(current_mode)

    ack = controller._set_protocol_mode(target_mode)

    assert (ack is not None) is expected_allowed

def test_serial_transport_queue_depth_is_reflected_in_runtime_telemetry(
    qapp: QApplication, runtime_config: RuntimeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    serial_runtime = replace(runtime_config, transport=replace(runtime_config.transport, kind="serial"))
    monkeypatch.setattr("gui.bench_app.controller.SerialMcuTransport", _StubSerialTransport)
    controller = BenchAppController(qapp, serial_runtime)
    controller.bench_runner = _RecordingRunner(())

    command = ScheduledCommand(lane=1, position_mm=200.0)
    controller.transport.send(command)

    queue_states: list[QueueState] = []
    controller.queue_state_requested.connect(lambda state: queue_states.append(state))
    controller._emit_runtime_state()

    assert queue_states[-1].depth == 2


def test_serial_transport_response_updates_latest_queue_observations(
    qapp: QApplication, runtime_config: RuntimeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    serial_runtime = replace(runtime_config, transport=replace(runtime_config.transport, kind="serial"))
    monkeypatch.setattr("gui.bench_app.controller.SerialMcuTransport", _StubSerialTransport)
    controller = BenchAppController(qapp, serial_runtime)

    controller.transport_response_received.emit(
        BenchLogEntry(
            frame_timestamp_s=0.1,
            trigger_generation_s=0.1,
            lane=1,
            decision="accept",
            rejection_reason=None,
            protocol_round_trip_ms=4.2,
            ack_code=AckCode.ACK,
            queue_depth=5,
            scheduler_state="ACTIVE",
            mode="AUTO",
            queue_cleared=True,
        )
    )

    assert controller._latest_transport_queue_depth == 5
    assert controller._latest_transport_queue_cleared is True
    assert controller._transport_queue_depth() == 5
    assert controller._transport_last_queue_cleared() is True


def test_controller_uses_esp32_transport_when_configured(
    qapp: QApplication, runtime_config: RuntimeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    esp32_runtime = replace(runtime_config, transport=replace(runtime_config.transport, kind="esp32"))
    monkeypatch.setattr("gui.bench_app.controller.Esp32McuTransport", _StubSerialTransport)

    controller = BenchAppController(qapp, esp32_runtime)

    assert isinstance(controller.transport, _StubSerialTransport)


def test_manual_fire_uses_scheduler_transport_send_without_send_command_side_channel(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    class _NoBypassTransport:
        def __init__(self) -> None:
            self.sent: list[ScheduledCommand] = []

        def send(self, command: ScheduledCommand) -> TransportResponse:
            self.sent.append(command)
            return TransportResponse(
                ack_code=AckCode.ACK,
                queue_depth=1,
                round_trip_ms=1.0,
                fault_state=FaultState.NORMAL,
                scheduler_state="ACTIVE",
                mode="MANUAL",
                queue_cleared=False,
            )

        def send_command(self, _command: str, _args: tuple[object, ...] = ()) -> None:
            raise AssertionError("manual fire must not bypass scheduler via send_command")

    transport = _NoBypassTransport()
    controller.transport = transport
    controller.window.manual_lane_input.setValue(3)
    controller.window.manual_position_input.setValue(245.0)

    ack = controller._send_poc_fire_command(reason="manual_fire_test")

    assert ack is not None and ack.status == "ACK"
    assert len(transport.sent) == 1
    assert transport.sent[0].lane == 3
    assert transport.sent[0].position_mm == pytest.approx(245.0)


def test_manual_fire_rejects_out_of_range_servo_values(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller.window.manual_lane_input.setValue(runtime_config.bench_gui.manual_servo.max_lane)
    controller.window.manual_position_input.setValue(runtime_config.bench_gui.manual_servo.max_position_mm + 1.0)

    ack = controller._send_poc_fire_command(reason="manual_fire_test")

    assert ack is None
    assert "out of range" in controller.window.last_command_label.text()
