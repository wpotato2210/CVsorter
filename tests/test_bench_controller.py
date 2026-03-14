from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    pytest.skip("PySide6 is required for GUI tests", allow_module_level=True)

from coloursorter.bench import BenchMode, FaultState
from coloursorter.config import RuntimeConfig
from gui.bench_app.app import QueueState
from gui.bench_app.controller import BenchAppController, ControllerState


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


@pytest.mark.gui_transition_gate
def test_illegal_replay_to_live_transition_keeps_runtime_ui_timer_consistent(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    overlays: list[str] = []
    entered_states: list[ControllerState] = []
    controller.lane_overlay_requested.connect(lambda text: overlays.append(text))
    controller._state_machine.entered.connect(lambda state: entered_states.append(state))
    observed_states: list[QueueState] = []
    controller.queue_state_requested.connect(lambda state: observed_states.append(state))
    replay_trigger_count = 0
    live_trigger_count = 0

    def _on_replay_trigger() -> None:
        nonlocal replay_trigger_count
        replay_trigger_count += 1

    def _on_live_trigger() -> None:
        nonlocal live_trigger_count
        live_trigger_count += 1

    controller._state_machine.start_replay.connect(_on_replay_trigger)
    controller._state_machine.start_live.connect(_on_live_trigger)

    replay_transitioned = controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")

    assert replay_transitioned is True
    assert replay_trigger_count == 1
    assert live_trigger_count == 0
    assert observed_states
    baseline_state = controller.runtime_state.controller_state
    baseline_timer_active = controller._cycle_timer.isActive()
    baseline_replay_enabled = controller.window.replay_button.isEnabled()
    baseline_live_enabled = controller.window.live_button.isEnabled()
    baseline_overlay_count = len(overlays)
    baseline_entered_count = len(entered_states)
    baseline_last_entered = entered_states[-1]
    baseline_overlay_label = controller.window.lane_overlay_label.text()
    baseline_queue_state_label = controller.window.queue_state_label.text()
    baseline_status_label = controller.window.status_label.text()
    baseline_status_bar_message = controller.window.statusBar().currentMessage()
    baseline_runtime_queue_state = observed_states[-1].controller_state
    baseline_runtime_run_state = observed_states[-1].run_state
    baseline_state_machine_state = controller._state_machine._current_state
    baseline_trigger_state = controller.runtime_state.controller_state

    live_transitioned = controller._transition_to(
        ControllerState.LIVE_RUNNING,
        overlay_text="Live mode active",
    )

    assert live_transitioned is False
    assert replay_trigger_count == 1
    assert live_trigger_count == 1
    assert controller.runtime_state.controller_state == ControllerState.REPLAY_RUNNING
    assert controller.runtime_state.controller_state == baseline_state
    assert controller._cycle_timer.isActive()
    assert controller._cycle_timer.isActive() == baseline_timer_active
    assert controller.window.replay_button.isEnabled() == baseline_replay_enabled
    assert controller.window.live_button.isEnabled() == baseline_live_enabled
    assert controller.window.lane_overlay_label.text() == baseline_overlay_label
    assert "Live mode active" not in overlays
    assert len(overlays) == baseline_overlay_count
    assert controller._pending_overlay is None
    assert len(entered_states) == baseline_entered_count
    assert entered_states[-1] == baseline_last_entered
    assert controller.runtime_state.controller_state == entered_states[-1]
    assert controller._state_machine._current_state == baseline_state_machine_state
    assert controller.window.queue_state_label.text() == baseline_queue_state_label
    assert controller.window.status_label.text() == baseline_status_label
    assert controller.window.statusBar().currentMessage() == baseline_status_bar_message
    assert "Live mode active" not in controller.window.lane_overlay_label.text()
    assert observed_states[-1].controller_state == baseline_runtime_queue_state
    assert observed_states[-1].run_state == baseline_runtime_run_state
    assert controller.runtime_state.controller_state == baseline_trigger_state




def test_safe_guardrail_rejection_uses_generic_rejection_semantics(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    assert controller._transition_to(ControllerState.SAFE, overlay_text="SAFE fault active") is True
    controller.runtime_state.fault_state = FaultState.SAFE

    overlays: list[str] = []
    observed_states: list[QueueState] = []
    controller.lane_overlay_requested.connect(lambda text: overlays.append(text))
    controller.queue_state_requested.connect(lambda state: observed_states.append(state))

    baseline_overlay_label = controller.window.lane_overlay_label.text()
    baseline_timer_active = controller._cycle_timer.isActive()

    transitioned = controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")

    assert transitioned is False
    assert controller.runtime_state.controller_state == ControllerState.SAFE
    assert controller._cycle_timer.isActive() == baseline_timer_active
    assert controller.window.lane_overlay_label.text() == baseline_overlay_label
    assert overlays == []
    assert controller._pending_overlay is None
    assert observed_states
    assert observed_states[-1].controller_state == ControllerState.SAFE.value
    assert observed_states[-1].run_state == ControllerState.SAFE.value

def test_transition_to_does_not_preassign_runtime_state_on_rejected_request(
    qapp: QApplication, runtime_config: RuntimeConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    transitioned = controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")
    assert transitioned is True

    baseline_state = controller.runtime_state.controller_state
    baseline_overlay_text = controller.window.lane_overlay_label.text()
    baseline_timer_active = controller._cycle_timer.isActive()

    monkeypatch.setattr(controller._state_machine, "request", lambda _state: False)

    transitioned = controller._transition_to(ControllerState.LIVE_RUNNING, overlay_text="Live mode active")

    assert transitioned is False
    assert controller.runtime_state.controller_state == baseline_state
    assert controller._cycle_timer.isActive() == baseline_timer_active
    assert controller.window.lane_overlay_label.text() == baseline_overlay_text
    assert controller._pending_overlay is None


def test_transition_to_rejected_request_keeps_runtime_and_ui_consistent_when_trigger_signal_fires(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    assert controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active") is True
    baseline_state = controller.runtime_state.controller_state
    baseline_timer_active = controller._cycle_timer.isActive()
    baseline_overlay_text = controller.window.lane_overlay_label.text()

    entered_states: list[ControllerState] = []
    overlays: list[str] = []
    live_trigger_count = 0

    controller._state_machine.entered.connect(lambda state: entered_states.append(state))
    controller.lane_overlay_requested.connect(lambda text: overlays.append(text))

    def _on_live_trigger() -> None:
        nonlocal live_trigger_count
        live_trigger_count += 1

    controller._state_machine.start_live.connect(_on_live_trigger)

    transitioned = controller._transition_to(ControllerState.LIVE_RUNNING, overlay_text="Live mode active")

    assert transitioned is False
    assert live_trigger_count == 1
    assert entered_states == []
    assert controller.runtime_state.controller_state == baseline_state
    assert controller._cycle_timer.isActive() == baseline_timer_active
    assert controller.window.lane_overlay_label.text() == baseline_overlay_text
    assert overlays == []
    assert controller._pending_overlay is None


class _StubFrameSource:
    def __init__(self, frame: object) -> None:
        self._frame = frame

    def next_frame(self) -> object:
        return self._frame


def test_next_frame_prefers_simulated_overlay_when_replay_mock_and_enabled(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    controller = BenchAppController(qapp, runtime_config)

    sentinel = object()
    controller._frame_source = _StubFrameSource(frame=sentinel)  # type: ignore[assignment]
    controller.runtime_state.mode = BenchMode.REPLAY

    frame = controller._next_frame()

    assert frame is not sentinel
    assert frame.frame_id == 0


def test_next_frame_uses_frame_source_when_simulated_overlay_disabled(
    qapp: QApplication, runtime_config: RuntimeConfig
) -> None:
    disabled_overlay_config = replace(
        runtime_config,
        frame_source=replace(runtime_config.frame_source, simulated_overlay=False),
    )
    controller = BenchAppController(qapp, disabled_overlay_config)

    sentinel = object()
    controller._frame_source = _StubFrameSource(frame=sentinel)  # type: ignore[assignment]
    controller.runtime_state.mode = BenchMode.REPLAY

    frame = controller._next_frame()

    assert frame is sentinel
