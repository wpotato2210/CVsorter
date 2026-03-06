from __future__ import annotations

import os
from pathlib import Path

import pytest

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    pytest.skip("PySide6 is required for GUI tests", allow_module_level=True)

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

    replay_transitioned = controller._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")

    assert replay_transitioned is True
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
    baseline_runtime_queue_state = observed_states[-1].controller_state
    baseline_runtime_run_state = observed_states[-1].run_state

    live_transitioned = controller.request_live_mode()

    assert live_transitioned is False
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
    assert controller.window.queue_state_label.text() == baseline_queue_state_label
    assert controller.window.status_label.text() == baseline_status_label
    assert observed_states[-1].controller_state == baseline_runtime_queue_state
    assert observed_states[-1].run_state == baseline_runtime_run_state
