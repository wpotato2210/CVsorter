from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    pytest.skip("PySide6 is required for GUI tests", allow_module_level=True)

from coloursorter.bench import AckCode, BenchLogEntry, FaultState
from coloursorter.bench.types import TransportResponse
from coloursorter.config import RuntimeConfig
from coloursorter.scheduler import ScheduledCommand
from gui.bench_app.app import QueueState
from gui.bench_app.controller import BenchAppController, ControllerState, GUI_TO_HOST_MODE, OperatorMode


class _StubSerialTransport:
    def __init__(self, *_args, **_kwargs) -> None:
        self._queue_depth = 0
        self._last_queue_cleared = False

    def send(self, _command: ScheduledCommand) -> TransportResponse:
        self._queue_depth = 2
        self._last_queue_cleared = False
        return TransportResponse(
            ack_code=AckCode.ACK,
            queue_depth=2,
            round_trip_ms=5.0,
            fault_state=FaultState.NORMAL,
            scheduler_state="ACTIVE",
            mode="AUTO",
            queue_cleared=False,
        )

    def current_fault_state(self) -> FaultState:
        return FaultState.NORMAL

    def current_queue_depth(self) -> int:
        return self._queue_depth

    def transport_queue_depth(self) -> int:
        return self._queue_depth

    def last_queue_cleared_observation(self) -> bool:
        return self._last_queue_cleared

    def transport_last_queue_cleared(self) -> bool:
        return self._last_queue_cleared


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


def test_mode_mapping_matches_host_values() -> None:
    assert GUI_TO_HOST_MODE[OperatorMode.AUTO] == "AUTO"
    assert GUI_TO_HOST_MODE[OperatorMode.MANUAL] == "MANUAL"
    assert GUI_TO_HOST_MODE[OperatorMode.SAFE] == "SAFE"


def test_state_machine_drives_running_and_idle_transitions(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")
    assert controller.runtime_state.controller_state == ControllerState.REPLAY_RUNNING
    assert controller._cycle_timer.isActive()

    controller._transition_to(ControllerState.IDLE, overlay_text="Homing complete")
    assert controller.runtime_state.controller_state == ControllerState.IDLE
    assert not controller._cycle_timer.isActive()


def test_transition_overlay_emits_only_after_confirmed_enter_callback(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    event_order: list[str] = []
    controller._state_machine.entered.connect(lambda state: event_order.append(f"entered:{state.value}"))
    controller.lane_overlay_requested.connect(lambda text: event_order.append(f"overlay:{text}"))

    controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")

    assert event_order == ["entered:replay_running", "overlay:Replay mode active"]
    assert controller.runtime_state.controller_state == ControllerState.REPLAY_RUNNING


def test_illegal_replay_to_live_transition_keeps_runtime_ui_timer_consistent(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    overlays: list[str] = []
    controller.lane_overlay_requested.connect(lambda text: overlays.append(text))
    observed: list[QueueState] = []
    controller.queue_state_requested.connect(lambda state: observed.append(state))

    controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")
    baseline_state = controller.runtime_state.controller_state
    baseline_timer_active = controller._cycle_timer.isActive()
    baseline_replay_enabled = controller.window.replay_button.isEnabled()
    baseline_live_enabled = controller.window.live_button.isEnabled()
    baseline_overlay_label = controller.window.lane_overlay_label.text()
    baseline_queue_state = observed[-1].controller_state
    baseline_run_state = observed[-1].run_state
    baseline_status_label = controller.window.status_label.text()
    baseline_overlay_count = len(overlays)

    controller._transition_to(ControllerState.LIVE_RUNNING, overlay_text="Live mode active")

    assert controller.runtime_state.controller_state == ControllerState.REPLAY_RUNNING
    assert controller.runtime_state.controller_state == baseline_state
    assert controller._cycle_timer.isActive()
    assert controller._cycle_timer.isActive() == baseline_timer_active
    assert controller.window.replay_button.isEnabled() == baseline_replay_enabled
    assert controller.window.live_button.isEnabled() == baseline_live_enabled
    assert controller.window.lane_overlay_label.text() == baseline_overlay_label
    assert controller.window.status_label.text() == baseline_status_label
    assert "Live mode active" not in overlays
    assert len(overlays) == baseline_overlay_count
    assert observed[-1].controller_state == baseline_queue_state
    assert observed[-1].run_state == baseline_run_state


def test_on_controller_state_entered_centralizes_runtime_timer_and_button_updates(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller._on_controller_state_entered(ControllerState.REPLAY_RUNNING)

    assert controller.runtime_state.controller_state == ControllerState.REPLAY_RUNNING
    assert controller._cycle_timer.isActive()
    assert controller.window.replay_button.isEnabled() is False
    assert controller.window.live_button.isEnabled() is False

    controller._on_controller_state_entered(ControllerState.IDLE)

    assert controller.runtime_state.controller_state == ControllerState.IDLE
    assert controller._cycle_timer.isActive() is False
    assert controller.window.replay_button.isEnabled() is True
    assert controller.window.live_button.isEnabled() is True

def test_safe_recovery_guardrails_follow_protocol(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller.runtime_state.fault_state = FaultState.SAFE
    controller._set_protocol_mode(OperatorMode.SAFE)
    controller._transition_to(ControllerState.SAFE, overlay_text="SAFE fault active")

    assert controller.recover_to_auto() is False
    assert controller.recover_safe_to_manual() is True
    assert controller.runtime_state.operator_mode == OperatorMode.MANUAL

    assert controller.recover_to_auto() is True
    assert controller.runtime_state.operator_mode == OperatorMode.AUTO


def test_runtime_state_updates_queue_scheduler_mode_labels(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller.runtime_state.scheduler_state = "ACTIVE"
    controller.runtime_state.operator_mode = OperatorMode.MANUAL

    observed: list[QueueState] = []
    controller.queue_state_requested.connect(lambda state: observed.append(state))
    controller._emit_runtime_state()

    state = observed[-1]
    assert state.scheduler_state == "ACTIVE"
    assert state.mode == "MANUAL"
    assert "mode=MANUAL" in controller.window.statusBar().currentMessage()


def test_serial_queue_depth_is_exposed_in_gui_state(
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
            protocol_round_trip_ms=4.0,
            ack_code=AckCode.ACK,
            queue_depth=2,
            scheduler_state="ACTIVE",
            mode="AUTO",
            queue_cleared=False,
        )
    )

    assert controller.window.queue_depth_label.text() == "Depth: 2/8"




def test_transport_response_signal_refreshes_queue_widgets_for_mock_path(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller.transport_response_received.emit(
        BenchLogEntry(
            frame_timestamp_s=0.1,
            trigger_generation_s=0.1,
            lane=1,
            decision="accept",
            rejection_reason=None,
            protocol_round_trip_ms=4.0,
            ack_code=AckCode.ACK,
            queue_depth=4,
            scheduler_state="ACTIVE",
            mode="MANUAL",
            queue_cleared=False,
        )
    )

    assert controller.window.queue_depth_label.text() == "Depth: 4/8"
    assert controller.window.scheduler_state_label.text() == "Scheduler: ACTIVE"
    assert controller.window.mode_label.text() == "Mode: MANUAL"


def test_serial_transport_response_signal_emits_real_queue_state_values(
    qapp: QApplication, runtime_config: RuntimeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    serial_runtime = replace(runtime_config, transport=replace(runtime_config.transport, kind="serial"))
    monkeypatch.setattr("gui.bench_app.controller.SerialMcuTransport", _StubSerialTransport)
    controller = BenchAppController(qapp, serial_runtime)

    emitted_states: list[QueueState] = []
    controller.queue_state_requested.connect(lambda state: emitted_states.append(state))

    controller.transport_response_received.emit(
        BenchLogEntry(
            frame_timestamp_s=0.3,
            trigger_generation_s=0.3,
            lane=3,
            decision="accept",
            rejection_reason=None,
            protocol_round_trip_ms=5.1,
            ack_code=AckCode.ACK,
            queue_depth=6,
            scheduler_state="ACTIVE",
            mode="AUTO",
            queue_cleared=True,
        )
    )

    assert emitted_states[-1].depth == 6
    assert controller._latest_transport_queue_depth == 6
    assert controller._latest_transport_queue_cleared is True
    assert controller.window.queue_depth_label.text() == "Depth: 6/8"


def test_queue_depth_falls_back_to_latest_transport_response_when_transport_has_no_depth_api(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller.transport = object()
    controller.transport_response_received.emit(
        BenchLogEntry(
            frame_timestamp_s=0.2,
            trigger_generation_s=0.2,
            lane=2,
            decision="reject",
            rejection_reason="rule",
            protocol_round_trip_ms=5.0,
            ack_code=AckCode.ACK,
            queue_depth=3,
            scheduler_state="ACTIVE",
            mode="AUTO",
            queue_cleared=False,
        )
    )

    assert controller.window.queue_depth_label.text() == "Depth: 3/8"


def test_safe_entry_updates_overlay_fault_and_mode(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller.runtime_state.fault_state = FaultState.SAFE
    controller._set_protocol_mode(OperatorMode.SAFE)
    controller._transition_to(ControllerState.SAFE, overlay_text="SAFE fault active")

    assert controller.window.lane_overlay_label.text() == "SAFE fault active"
    assert controller.window.safe_label.text() == "SAFE: on"
    assert controller.window.mode_label.text() == "Mode: SAFE"


def test_log_mode_updates_runtime_mode_from_transport_feedback(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller.runtime_state.controller_state = ControllerState.REPLAY_RUNNING
    controller.runtime_state.scheduler_state = "IDLE"
    controller.runtime_state.operator_mode = OperatorMode.AUTO

    controller.transport_response_received.emit(
        BenchLogEntry(
            frame_timestamp_s=0.1,
            trigger_generation_s=0.1,
            lane=1,
            decision="accept",
            rejection_reason=None,
            protocol_round_trip_ms=4.0,
            ack_code=AckCode.ACK,
            scheduler_state="ACTIVE",
            mode="MANUAL",
            queue_depth=2,
            queue_cleared=False,
        )
    )

    assert controller.window.scheduler_state_label.text() == "Scheduler: ACTIVE"
    assert controller.window.mode_label.text() == "Mode: MANUAL"


def test_selector_values_drive_serial_transport_config(
    qapp: QApplication, runtime_config: RuntimeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    serial_runtime = replace(runtime_config, transport=replace(runtime_config.transport, kind="serial"))
    observed: list[object] = []

    class _CaptureSerialTransport(_StubSerialTransport):
        def __init__(self, config, *_args, **_kwargs) -> None:
            observed.append(config)
            super().__init__()

    monkeypatch.setattr("gui.bench_app.controller.SerialMcuTransport", _CaptureSerialTransport)
    controller = BenchAppController(qapp, serial_runtime)

    controller.window.mcu_selector.setCurrentText("serial")
    controller.window.com_selector.setCurrentText("COM3")
    controller.window.baud_selector.setCurrentText("230400")
    controller.on_serial_disconnect_clicked()
    controller.on_serial_connect_clicked()

    assert observed
    config = observed[-1]
    assert config.port == "COM3"
    assert config.baud == 230400


def test_gui_selectors_are_initialized_from_runtime_config(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    assert controller.window.mcu_selector.currentText() == runtime_config.transport.kind
    assert controller.window.com_selector.currentText() == runtime_config.transport.serial_port
    assert controller.window.baud_selector.currentText() == str(runtime_config.transport.serial_baud)
    assert controller.window.log_level_selector.currentText() == runtime_config.bench_gui.default_log_level


def test_manual_fire_is_blocked_while_auto_cycle_active(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller.runtime_state.controller_state = ControllerState.REPLAY_RUNNING
    controller.runtime_state.operator_mode = OperatorMode.AUTO

    controller.on_fire_test_clicked()

    assert "AUTO cycle active" in controller.window.last_command_label.text()


def test_transport_reconfiguration_is_blocked_while_auto_cycle_active(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)
    controller.runtime_state.controller_state = ControllerState.LIVE_RUNNING
    controller.runtime_state.operator_mode = OperatorMode.AUTO
    original_kind = controller._selected_transport_kind

    controller.on_mcu_selector_changed("serial")
    controller.on_serial_connect_clicked()

    assert controller._selected_transport_kind == original_kind
    assert "blocked: AUTO cycle active" in controller.window.serial_status_label.text()


def test_gui_health_summary_shows_run_state_and_fault_counters(qapp: QApplication, runtime_config: RuntimeConfig) -> None:
    controller = BenchAppController(qapp, runtime_config)

    controller.transport_response_received.emit(
        BenchLogEntry(
            frame_timestamp_s=0.1,
            trigger_generation_s=0.1,
            lane=1,
            decision="reject",
            rejection_reason="classified_reject",
            protocol_round_trip_ms=4.0,
            ack_code=AckCode.NACK_SAFE,
            queue_depth=1,
            scheduler_state="SAFE",
            mode="SAFE",
            fault_event="SEND_BUDGET_EXCEEDED",
        )
    )

    status = controller.window.status_label.text()
    assert "Run=" in status
    assert "rejects=1" in status
    assert "NACK faults=1" in status
