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

    def last_queue_cleared_observation(self) -> bool:
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

    controller.transport.send(ScheduledCommand(lane=1, position_mm=100.0))
    controller._emit_runtime_state()

    assert controller.window.queue_depth_label.text() == "Depth: 2/8"


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
    log_entry = BenchLogEntry(
        frame_timestamp_s=0.1,
        trigger_generation_s=0.1,
        lane=1,
        decision="accept",
        rejection_reason=None,
        protocol_round_trip_ms=4.0,
        ack_code=AckCode.ACK,
        scheduler_state="ACTIVE",
        mode="MANUAL",
    )

    controller.runtime_state.controller_state = ControllerState.REPLAY_RUNNING
    controller.runtime_state.scheduler_state = "IDLE"
    controller.runtime_state.operator_mode = OperatorMode.AUTO

    controller._session_logs.append(log_entry)
    controller.runtime_state.scheduler_state = log_entry.scheduler_state
    controller.runtime_state.operator_mode = OperatorMode(log_entry.mode)
    controller._emit_runtime_state()

    assert controller.window.scheduler_state_label.text() == "Scheduler: ACTIVE"
    assert controller.window.mode_label.text() == "Mode: MANUAL"
