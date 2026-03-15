from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import logging
import threading
import time
from typing import Any, Callable

import cv2
import numpy as np
from PySide6.QtCore import QObject, QEventLoop, QTimer, Signal, Slot
from PySide6.QtStateMachine import QState, QStateMachine
from PySide6.QtWidgets import QApplication, QMessageBox

from coloursorter.bench import (
    AckCode,
    BenchFrameSource,
    BenchFrame,
    BenchLogEntry,
    BenchMode,
    BenchRunner,
    EncoderConfig,
    FaultState,
    FrameSourceError,
    LiveConfig,
    LiveFrameSource,
    Esp32McuTransport,
    MockMcuTransport,
    MockTransportConfig,
    ReplayConfig,
    ReplayFrameSource,
    VirtualEncoder,
    evaluate_logs,
    scenarios_from_thresholds,
)
from coloursorter.bench.serial_transport import SerialMcuTransport, SerialTransportConfig, SerialTransportError
from coloursorter.config import RuntimeConfig
from coloursorter.scheduler import ScheduledCommand
from coloursorter.deploy import DetectionError, OpenCvDetectionProvider, PipelineRunner
from coloursorter.eval.reject_profiles import (
    RejectProfileValidationError,
    default_profile,
    load_reject_profiles,
    selected_thresholds,
)
from coloursorter.protocol import OpenSpecV3Host, is_mode_transition_allowed
from coloursorter.protocol.constants import LANE_MAX, LANE_MIN, TRIGGER_MM_MAX, TRIGGER_MM_MIN
from coloursorter.serial_interface import AckResponse, parse_ack_tokens, parse_frame, serialize_packet

from .app import BenchMainWindow, QueueState


LOGGER = logging.getLogger(__name__)


def _resolve_runtime_reject_thresholds(project_root: Path) -> dict[str, float]:
    profiles_path = project_root / "configs" / "reject_profiles.yaml"
    try:
        profiles, selected_name = load_reject_profiles(profiles_path)
        resolved = selected_thresholds(profiles, selected_name)
    except RejectProfileValidationError as exc:
        resolved = default_profile().thresholds
        LOGGER.warning(
            "Failed to load reject profiles from %s: %s. Falling back to default reject thresholds.",
            profiles_path,
            exc,
        )
    return {key: float(resolved[key]) for key in sorted(resolved)}


@dataclass(frozen=True)
class BenchTransportConfig:
    max_queue_depth: int
    base_round_trip_ms: float
    per_item_penalty_ms: float


@dataclass(frozen=True)
class BenchEncoderConfig:
    pulses_per_revolution: int
    belt_speed_mm_per_s: float
    pulley_circumference_mm: float
    dropout_ratio: float


class QueueConsumptionPolicy(str, Enum):
    NONE = "none"
    ONE_PER_TICK = "one_per_tick"
    ALL = "all"


@dataclass(frozen=True)
class BenchCycleConfig:
    period_ms: int
    queue_consumption_policy: QueueConsumptionPolicy


@dataclass(frozen=True)
class WatchdogBudgetConfig:
    frame_acquire_detect_ms: float
    decision_schedule_ms: float
    transport_ms: float
    cycle_budget_ms: float


@dataclass
class QueueBackpressureMetrics:
    offered: int = 0
    accepted: int = 0
    dropped_oldest: int = 0
    dropped_newest: int = 0


class BoundedDropQueue:
    def __init__(self, maxlen: int, *, drop_oldest: bool) -> None:
        self._queue: deque[Any] = deque(maxlen=maxlen)
        self._cond = threading.Condition()
        self._closed = False
        self._drop_oldest = drop_oldest
        self.metrics = QueueBackpressureMetrics()

    def put(self, item: Any) -> None:
        with self._cond:
            self.metrics.offered += 1
            if self._closed:
                self.metrics.dropped_newest += 1
                return
            if len(self._queue) == self._queue.maxlen:
                if self._drop_oldest:
                    self._queue.popleft()
                    self.metrics.dropped_oldest += 1
                else:
                    self.metrics.dropped_newest += 1
                    return
            self._queue.append(item)
            self.metrics.accepted += 1
            self._cond.notify()

    def get(self, timeout_s: float | None = None) -> Any | None:
        with self._cond:
            if timeout_s is None:
                while not self._queue and not self._closed:
                    self._cond.wait()
            else:
                end_at = time.monotonic() + timeout_s
                while not self._queue and not self._closed:
                    remaining = end_at - time.monotonic()
                    if remaining <= 0:
                        return None
                    self._cond.wait(timeout=remaining)
            if not self._queue:
                return None
            return self._queue.popleft()

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()


@dataclass(frozen=True)
class _DetectedFrameBatch:
    frame: BenchFrame
    frame_rgb: object
    detections: tuple[object, ...]
    previous_timestamp_s: float
    stage_ms: dict[str, float]


@dataclass(frozen=True)
class _WorkerEvent:
    kind: str
    payload: object


@dataclass(frozen=True)
class _UiActionEvent:
    kind: str
    payload: object


class ControllerState(str, Enum):
    IDLE = "idle"
    REPLAY_RUNNING = "replay_running"
    LIVE_RUNNING = "live_running"
    FAULTED = "faulted"
    SAFE = "safe"


class OperatorMode(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    SAFE = "SAFE"


GUI_TO_HOST_MODE = {
    OperatorMode.AUTO: "AUTO",
    OperatorMode.MANUAL: "MANUAL",
    OperatorMode.SAFE: "SAFE",
}


class RuntimeState:
    def __init__(self, *, mode: BenchMode, previous_timestamp_s: float, fault_state: FaultState, operator_mode: OperatorMode) -> None:
        self.mode = mode
        self.previous_timestamp_s = previous_timestamp_s
        self.fault_state = fault_state
        self.operator_mode = operator_mode
        self.scheduler_state = "IDLE"
        self._controller_state = ControllerState.IDLE

    @property
    def controller_state(self) -> ControllerState:
        return self._controller_state

    def _set_controller_state(self, state: ControllerState) -> None:
        self._controller_state = state


class BenchControllerStateMachine(QObject):
    entered = Signal(object)

    start_replay = Signal()
    start_live = Signal()
    go_idle = Signal()
    set_faulted = Signal()
    set_safe = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._machine = QStateMachine(self)

        self._idle = QState()
        self._replay = QState()
        self._live = QState()
        self._faulted = QState()
        self._safe = QState()

        self._machine.addState(self._idle)
        self._machine.addState(self._replay)
        self._machine.addState(self._live)
        self._machine.addState(self._faulted)
        self._machine.addState(self._safe)
        self._machine.setInitialState(self._idle)

        self._idle.addTransition(self.start_replay, self._replay)
        self._idle.addTransition(self.start_live, self._live)
        self._idle.addTransition(self.set_faulted, self._faulted)
        self._idle.addTransition(self.set_safe, self._safe)

        self._replay.addTransition(self.go_idle, self._idle)
        self._replay.addTransition(self.set_faulted, self._faulted)
        self._replay.addTransition(self.set_safe, self._safe)

        self._live.addTransition(self.go_idle, self._idle)
        self._live.addTransition(self.set_faulted, self._faulted)
        self._live.addTransition(self.set_safe, self._safe)

        self._faulted.addTransition(self.go_idle, self._idle)
        self._faulted.addTransition(self.set_safe, self._safe)

        self._safe.addTransition(self.go_idle, self._idle)

        self._idle.entered.connect(lambda: self.entered.emit(ControllerState.IDLE))
        self._replay.entered.connect(lambda: self.entered.emit(ControllerState.REPLAY_RUNNING))
        self._live.entered.connect(lambda: self.entered.emit(ControllerState.LIVE_RUNNING))
        self._faulted.entered.connect(lambda: self.entered.emit(ControllerState.FAULTED))
        self._safe.entered.connect(lambda: self.entered.emit(ControllerState.SAFE))

        self._machine.start()
        self._current_state = ControllerState.IDLE
        self.entered.connect(self._on_entered)
        self._allowed_transitions: dict[ControllerState, frozenset[ControllerState]] = {
            ControllerState.IDLE: frozenset(
                {
                    ControllerState.REPLAY_RUNNING,
                    ControllerState.LIVE_RUNNING,
                    ControllerState.FAULTED,
                    ControllerState.SAFE,
                }
            ),
            ControllerState.REPLAY_RUNNING: frozenset({ControllerState.IDLE, ControllerState.FAULTED, ControllerState.SAFE}),
            ControllerState.LIVE_RUNNING: frozenset({ControllerState.IDLE, ControllerState.FAULTED, ControllerState.SAFE}),
            ControllerState.FAULTED: frozenset({ControllerState.IDLE, ControllerState.SAFE}),
            ControllerState.SAFE: frozenset({ControllerState.IDLE}),
        }

    @Slot(object)
    def _on_entered(self, state: ControllerState) -> None:
        self._current_state = state

    def request(self, state: ControllerState) -> bool:
        if state == self._current_state:
            return False
        allowed_targets = self._allowed_transitions.get(self._current_state, frozenset())
        # Audit P0.1: reject illegal edges without emitting triggers.
        if state not in allowed_targets:
            return False
        trigger_by_state: dict[ControllerState, Signal] = {
            ControllerState.REPLAY_RUNNING: self.start_replay,
            ControllerState.LIVE_RUNNING: self.start_live,
            ControllerState.IDLE: self.go_idle,
            ControllerState.FAULTED: self.set_faulted,
            ControllerState.SAFE: self.set_safe,
        }
        trigger = trigger_by_state.get(state)
        if trigger is None:
            return False
        trigger.emit()
        return True


class BenchAppController(QObject):
    _TRANSITION_TIMEOUT_MS = 120

    frame_preview_requested = Signal(bytes, int, int)
    lane_overlay_requested = Signal(str)
    queue_state_requested = Signal(object)
    fault_state_requested = Signal(object)
    log_entry_requested = Signal(object)
    mode_changed = Signal(object)
    transport_response_received = Signal(object)

    def __init__(self, app: QApplication, runtime_config: RuntimeConfig) -> None:
        super().__init__()
        self._app = app
        self._runtime_config = runtime_config
        project_root = Path(__file__).resolve().parents[2]
        self.runtime_reject_thresholds = _resolve_runtime_reject_thresholds(project_root)
        self.window = BenchMainWindow()
        self.trigger_threshold = runtime_config.baseline_run.detector_threshold
        self.belt_speed_mm_s = 140.0
        self._serial_connected = False
        self._selected_transport_kind = runtime_config.transport.kind
        self._selected_serial_port = runtime_config.transport.serial_port
        self._selected_serial_baud = runtime_config.transport.serial_baud
        self._selected_log_level = runtime_config.bench_gui.default_log_level

        self.transport_config = BenchTransportConfig(
            max_queue_depth=runtime_config.transport.max_queue_depth,
            base_round_trip_ms=runtime_config.transport.base_round_trip_ms,
            per_item_penalty_ms=runtime_config.transport.per_item_penalty_ms,
        )
        self.encoder_config = BenchEncoderConfig(
            pulses_per_revolution=2048,
            belt_speed_mm_per_s=140.0,
            pulley_circumference_mm=210.0,
            dropout_ratio=0.0,
        )
        self.runtime_state = RuntimeState(
            mode=BenchMode(runtime_config.frame_source.mode),
            previous_timestamp_s=0.0,
            fault_state=FaultState.NORMAL,
            operator_mode=OperatorMode.AUTO,
        )
        self._pending_overlay: str | None = None
        self._pending_overlay_state: ControllerState | None = None
        # Audit P1.4: transition token for pending overlay lifecycle; invalidated
        # on every request so delayed singleShot emissions cannot leak.
        self._pending_overlay_token = 0
        self._transition_request_token = 0
        self._transition_in_progress = False
        self._last_transition_diagnostics: dict[str, object] = {}
        # Audit P2.7: gate modal live prompt in automation/non-interactive runs.
        self._allow_blocking_live_prompt = os.environ.get("CVSORTER_ALLOW_BLOCKING_PROMPTS", "0") == "1"
        self.cycle_config = BenchCycleConfig(
            period_ms=runtime_config.cycle_timing.period_ms,
            queue_consumption_policy=QueueConsumptionPolicy(runtime_config.cycle_timing.queue_consumption_policy),
        )
        self.watchdog_config = WatchdogBudgetConfig(
            frame_acquire_detect_ms=float(self.cycle_config.period_ms),
            decision_schedule_ms=float(self.cycle_config.period_ms),
            transport_ms=float(self.cycle_config.period_ms),
            cycle_budget_ms=float(self.cycle_config.period_ms),
        )

        replay_path = Path(runtime_config.frame_source.replay_path)
        if not replay_path.is_absolute():
            replay_path = project_root / replay_path
        self.replay_source = ReplayFrameSource(
            replay_path,
            ReplayConfig(frame_period_s=runtime_config.frame_source.replay_frame_period_s),
        )
        self.live_config = LiveConfig(
            camera_index=runtime_config.camera.camera_index,
            frame_period_s=runtime_config.camera.frame_period_s,
        )
        self.pipeline = PipelineRunner(
            lane_config_path=project_root / "configs" / "lane_geometry.yaml",
            calibration_path=project_root / "configs" / "calibration.json",
        )
        setattr(self.pipeline, "runtime_reject_thresholds", dict(self.runtime_reject_thresholds))
        if runtime_config.transport.kind in {"serial", "esp32"}:
            transport_cls = SerialMcuTransport if runtime_config.transport.kind == "serial" else Esp32McuTransport
            self.transport = transport_cls(
                config=SerialTransportConfig(
                    port=runtime_config.transport.serial_port,
                    baud=runtime_config.transport.serial_baud,
                    timeout_s=runtime_config.transport.serial_timeout_s,
                )
            )
            self._serial_connected = True
        else:
            self.transport = MockMcuTransport(
                config=MockTransportConfig(
                    max_queue_depth=self.transport_config.max_queue_depth,
                    base_round_trip_ms=self.transport_config.base_round_trip_ms,
                    per_item_penalty_ms=self.transport_config.per_item_penalty_ms,
                )
            )
        self.encoder = VirtualEncoder(
            EncoderConfig(
                pulses_per_revolution=self.encoder_config.pulses_per_revolution,
                belt_speed_mm_per_s=self.encoder_config.belt_speed_mm_per_s,
                pulley_circumference_mm=self.encoder_config.pulley_circumference_mm,
                dropout_ratio=self.encoder_config.dropout_ratio,
            )
        )
        self.bench_runner = BenchRunner(self.pipeline, self.transport, self.encoder)
        self._protocol_host = OpenSpecV3Host(max_queue_depth=self.transport_config.max_queue_depth)
        self._detector = OpenCvDetectionProvider()
        setattr(self._detector, "runtime_reject_thresholds", dict(self.runtime_reject_thresholds))
        self._selected_scenarios = tuple(
            s for s in scenarios_from_thresholds(runtime_config.scenario_thresholds) if s.name == "nominal"
        )
        self._session_logs: list[BenchLogEntry] = []
        self._audit_trail: list[dict[str, object]] = []
        self._frame_source: BenchFrameSource | None = None
        self._use_simulated_live_feed = False
        self._simulated_overlay_enabled = runtime_config.frame_source.simulated_overlay
        self._degraded_mode_active = False
        self._simulated_frame_id = 0
        self._latest_transport_queue_depth = 0
        self._latest_transport_queue_cleared = False
        self._latest_transport_queue_cleared_seq = 0
        self._reject_count = 0
        self._ack_fault_count = 0
        self._nack_fault_count = 0
        self._frame_transport_queue = BoundedDropQueue(maxlen=2, drop_oldest=True)
        self._ui_event_queue = BoundedDropQueue(maxlen=64, drop_oldest=True)
        self._ui_action_queue = BoundedDropQueue(maxlen=128, drop_oldest=False)
        self._acquire_requests = BoundedDropQueue(maxlen=2, drop_oldest=False)
        self._worker_stop = threading.Event()
        self._frame_worker_thread = threading.Thread(target=self._frame_worker_loop, name="bench-frame-worker", daemon=True)
        self._transport_worker_thread = threading.Thread(
            target=self._transport_worker_loop,
            name="bench-transport-worker",
            daemon=True,
        )
        self._frame_worker_thread.start()
        self._transport_worker_thread.start()
        self._cycle_timer = QTimer(self)
        self._ui_action_timer = QTimer(self)
        self._ui_action_timer.setInterval(0)
        self._ui_action_timer.timeout.connect(self._drain_ui_action_events)
        self._cycle_timer.setInterval(self.cycle_config.period_ms)
        self._cycle_timer.timeout.connect(self._on_cycle_tick)

        self._state_machine = BenchControllerStateMachine(self)
        self._state_machine.entered.connect(self._on_controller_state_entered)
        # Flush initial state-machine entered event deterministically during init
        # so later transition observers only see transition-related events.
        self._app.processEvents()

        self._app.aboutToQuit.connect(self.shutdown)
        self._connect_view_actions()
        self._connect_view_updates()
        self._init_selector_controls_from_config()
        self.mode_changed.connect(self._on_mode_changed)
        self.transport_response_received.connect(self._on_transport_response_received)
        self._set_serial_status(self._serial_connected)

    @Slot()
    def shutdown(self) -> None:
        self._worker_stop.set()
        self._acquire_requests.close()
        self._frame_transport_queue.close()
        self._ui_event_queue.close()
        self._ui_action_queue.close()
        if self._frame_worker_thread.is_alive():
            self._frame_worker_thread.join(timeout=0.2)
        if self._transport_worker_thread.is_alive():
            self._transport_worker_thread.join(timeout=0.2)

    def start(self) -> None:
        self.window.resize(1200, 900)
        self.window.show()

    def _connect_view_actions(self) -> None:
        self.window.replay_button.clicked.connect(lambda: self._enqueue_ui_action("replay", None))
        self.window.live_button.clicked.connect(lambda: self._enqueue_ui_action("live", None))
        self.window.home_button.clicked.connect(lambda: self._enqueue_ui_action("home", None))
        self.window.serial_connect_button.clicked.connect(lambda: self._enqueue_ui_action("serial_connect", None))
        self.window.serial_disconnect_button.clicked.connect(lambda: self._enqueue_ui_action("serial_disconnect", None))
        self.window.fire_test_button.clicked.connect(lambda: self._enqueue_ui_action("fire_test", None))
        self.window.trigger_threshold_input.valueChanged.connect(
            lambda value: self._enqueue_ui_action("trigger_threshold", float(value))
        )
        self.window.belt_speed_input.valueChanged.connect(lambda value: self._enqueue_ui_action("belt_speed", float(value)))
        self.window.mcu_selector.currentTextChanged.connect(lambda value: self._enqueue_ui_action("mcu_selector", value))
        self.window.com_selector.currentTextChanged.connect(lambda value: self._enqueue_ui_action("com_selector", value))
        self.window.baud_selector.currentTextChanged.connect(lambda value: self._enqueue_ui_action("baud_selector", value))
        self.window.log_level_selector.currentTextChanged.connect(lambda value: self._enqueue_ui_action("log_level", value))
        self.window.clear_log_button.clicked.connect(lambda: self._enqueue_ui_action("clear_log", None))

    def _enqueue_ui_action(self, kind: str, payload: object) -> None:
        self._ui_action_queue.put(_UiActionEvent(kind=kind, payload=payload))
        if not self._ui_action_timer.isActive():
            self._ui_action_timer.start()

    def _drain_ui_action_events(self) -> None:
        handlers: dict[str, Callable[[object], None]] = {
            "replay": lambda _payload: self.on_replay_clicked(),
            "live": lambda _payload: self.on_live_clicked(),
            "home": lambda _payload: self.on_home_clicked(),
            "serial_connect": lambda _payload: self.on_serial_connect_clicked(),
            "serial_disconnect": lambda _payload: self.on_serial_disconnect_clicked(),
            "fire_test": lambda _payload: self.on_fire_test_clicked(),
            "trigger_threshold": lambda payload: self.on_trigger_threshold_changed(float(payload)),
            "belt_speed": lambda payload: self.on_belt_speed_changed(float(payload)),
            "mcu_selector": lambda payload: self.on_mcu_selector_changed(str(payload)),
            "com_selector": lambda payload: self.on_com_selector_changed(str(payload)),
            "baud_selector": lambda payload: self.on_baud_selector_changed(str(payload)),
            "log_level": lambda payload: self.on_log_level_changed(str(payload)),
            "clear_log": lambda _payload: self.on_clear_log_clicked(),
        }
        while True:
            event = self._ui_action_queue.get(timeout_s=0.0)
            if event is None:
                self._ui_action_timer.stop()
                return
            if not isinstance(event, _UiActionEvent):
                continue
            handler = handlers.get(event.kind)
            if handler is not None:
                handler(event.payload)

    def _connect_view_updates(self) -> None:
        self.frame_preview_requested.connect(self.window.update_frame_preview)
        self.lane_overlay_requested.connect(self.window.set_lane_overlay)
        self.queue_state_requested.connect(self.window.set_queue_state)
        self.fault_state_requested.connect(self.window.set_fault_state)
        self.log_entry_requested.connect(self.window.append_log_entry)

    def _init_selector_controls_from_config(self) -> None:
        gui = self._runtime_config.bench_gui

        self.window.mcu_selector.clear()
        self.window.mcu_selector.addItems(list(gui.mcu_options))
        self._set_combo_value(self.window.mcu_selector, self._selected_transport_kind)

        self.window.com_selector.clear()
        self.window.com_selector.addItems(list(gui.com_port_options))
        self._set_combo_value(self.window.com_selector, self._selected_serial_port)

        self.window.baud_selector.clear()
        self.window.baud_selector.addItems([str(v) for v in gui.baud_options])
        self._set_combo_value(self.window.baud_selector, str(self._selected_serial_baud))

        self.window.log_level_selector.clear()
        self.window.log_level_selector.addItems(list(gui.log_level_options))
        self._set_combo_value(self.window.log_level_selector, gui.default_log_level)

        manual = gui.manual_servo
        self.window.manual_lane_input.setRange(LANE_MIN, LANE_MAX)
        self.window.manual_lane_input.setValue(manual.default_lane)
        self.window.manual_position_input.setRange(TRIGGER_MM_MIN, TRIGGER_MM_MAX)
        self.window.manual_position_input.setValue(manual.default_position_mm)
        self.window.log_autoscroll_checkbox.setChecked(True)

    @staticmethod
    def _set_combo_value(combo, value: str) -> None:
        idx = combo.findText(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)


    def _set_last_command_status(self, status: str) -> None:
        self.window.set_last_command_status(status)

    def _set_serial_status(self, connected: bool, detail: str = "") -> None:
        label = "connected" if connected else "disconnected"
        suffix = f" ({detail})" if detail else ""
        self.window.serial_status_label.setText(f"Serial: {label}{suffix}")

    def _emit_runtime_state(self) -> None:
        self.queue_state_requested.emit(
            QueueState(
                depth=self._transport_queue_depth(),
                capacity=self.transport_config.max_queue_depth,
                controller_state=self.runtime_state.controller_state.value,
                scheduler_state=self.runtime_state.scheduler_state,
                mode=GUI_TO_HOST_MODE[self.runtime_state.operator_mode],
                degraded_mode=self._degraded_mode_active,
                run_state=self.runtime_state.controller_state.value,
                reject_count=self._reject_count,
                ack_fault_count=self._ack_fault_count,
                nack_fault_count=self._nack_fault_count,
            )
        )
        self.fault_state_requested.emit(self.runtime_state.fault_state)

    def _on_controller_state_entered(self, state: ControllerState) -> None:
        self.runtime_state._set_controller_state(state)
        self._emit_runtime_state()
        if state == ControllerState.SAFE and self.runtime_state.operator_mode != OperatorMode.SAFE:
            self._set_protocol_mode(OperatorMode.SAFE)
        running = state in {ControllerState.REPLAY_RUNNING, ControllerState.LIVE_RUNNING}
        if running and not self._cycle_timer.isActive():
            self._cycle_timer.start()
        if not running and self._cycle_timer.isActive():
            self._cycle_timer.stop()

        self._update_buttons_for_controller_state(state)
        self._update_buttons_for_mode(self.runtime_state.operator_mode)
        if self._pending_overlay is not None and self._pending_overlay_state == state:
            pending_overlay = self._pending_overlay
            pending_token = self._pending_overlay_token

            def _emit_pending_overlay() -> None:
                if pending_token != self._pending_overlay_token:
                    return
                self.lane_overlay_requested.emit(pending_overlay)
                self._pending_overlay = None
                self._pending_overlay_state = None

            QTimer.singleShot(0, _emit_pending_overlay)

    def _on_state_entered(self, state: ControllerState) -> None:
        self._on_controller_state_entered(state)

    @Slot(object)
    def _on_mode_changed(self, mode: OperatorMode) -> None:
        self._update_buttons_for_mode(mode)
        self._emit_runtime_state()

    @Slot(object)
    def _on_transport_response_received(self, log_entry: BenchLogEntry) -> None:
        self._update_transport_queue_observation(log_entry.queue_depth, log_entry.queue_cleared)
        if log_entry.decision == "reject":
            self._reject_count += 1
        if log_entry.ack_code == AckCode.ACK and log_entry.fault_event:
            self._ack_fault_count += 1
        if log_entry.ack_code != AckCode.ACK:
            self._nack_fault_count += 1
        self.runtime_state.scheduler_state = log_entry.scheduler_state
        self._set_operator_mode(OperatorMode(log_entry.mode))
        self._apply_protocol_queue_side_effects(log_entry.queue_cleared)
        self._emit_runtime_state()

    def _set_operator_mode(self, mode: OperatorMode) -> None:
        if self.runtime_state.operator_mode == mode:
            return
        self.runtime_state.operator_mode = mode
        self.mode_changed.emit(mode)

    def _update_buttons_for_controller_state(self, state: ControllerState) -> None:
        if state == ControllerState.IDLE:
            self.window.replay_button.setEnabled(True)
            self.window.live_button.setEnabled(True)
        elif state == ControllerState.REPLAY_RUNNING:
            self.window.replay_button.setEnabled(False)
            self.window.live_button.setEnabled(False)
        elif state == ControllerState.LIVE_RUNNING:
            self.window.replay_button.setEnabled(False)
            self.window.live_button.setEnabled(False)
        elif state == ControllerState.SAFE:
            self.window.replay_button.setEnabled(False)
            self.window.live_button.setEnabled(False)
        else:
            self.window.replay_button.setEnabled(False)
            self.window.live_button.setEnabled(False)
        self.window.home_button.setEnabled(state != ControllerState.FAULTED)

    def _update_buttons_for_mode(self, mode: OperatorMode) -> None:
        if mode == OperatorMode.SAFE:
            self.window.home_button.setText("Clear SAFE")
        else:
            self.window.home_button.setText("Home")

    def _is_auto_cycle_active(self) -> bool:
        return (
            self.runtime_state.operator_mode == OperatorMode.AUTO
            and self.runtime_state.controller_state in {ControllerState.REPLAY_RUNNING, ControllerState.LIVE_RUNNING}
        )

    def _capture_queue_state(self) -> dict[str, object]:
        return {
            "depth": self._transport_queue_depth(),
            "scheduler_state": self.runtime_state.scheduler_state,
            "controller_state": self.runtime_state.controller_state.value,
        }

    def _audit_operator_command(
        self,
        command: str,
        *,
        outcome: str,
        before_mode: OperatorMode,
        queue_before: dict[str, object],
    ) -> None:
        queue_after = self._capture_queue_state()
        audit_event = {
            "event": "operator_action",
            "command": command,
            "outcome": outcome,
            "before_mode": before_mode.value,
            "after_mode": self.runtime_state.operator_mode.value,
            "queue_before": queue_before,
            "queue_after": queue_after,
        }
        self._audit_trail.append(audit_event)
        LOGGER.info(
            "operator_command=%s outcome=%s before_mode=%s after_mode=%s queue_before=%s queue_after=%s",
            command,
            outcome,
            before_mode.value,
            self.runtime_state.operator_mode.value,
            queue_before,
            queue_after,
        )

    def _set_degraded_mode(self, active: bool, reason: str = "") -> None:
        self._degraded_mode_active = active
        if active:
            self.window.statusBar().showMessage(f"DEGRADED MODE: {reason}")
            self.lane_overlay_requested.emit(f"DEGRADED: {reason}")
            self._set_protocol_mode(OperatorMode.SAFE)
            self.runtime_state.scheduler_state = "IDLE"
        self._emit_runtime_state()

    def _set_transition_diagnostics(
        self,
        *,
        requested_state: ControllerState,
        previous_state: ControllerState,
        result: str,
        reason: str,
        token: int,
    ) -> None:
        self._last_transition_diagnostics = {
            "requested": requested_state.value,
            "previous": previous_state.value,
            "current": self.runtime_state.controller_state.value,
            "result": result,
            "reason": reason,
            "token": token,
        }

    def _wait_for_target_state(self, target_state: ControllerState, *, timeout_ms: int = _TRANSITION_TIMEOUT_MS) -> bool:
        # Audit P0.2: bounded target-state latch (no broad processEvents drains).
        if self.runtime_state.controller_state == target_state:
            return True
        loop = QEventLoop(self)
        completed = {"done": False}

        def _on_entered(state: ControllerState) -> None:
            if state == target_state:
                completed["done"] = True
                loop.quit()

        timeout_timer = QTimer(self)
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(loop.quit)
        self._state_machine.entered.connect(_on_entered)
        timeout_timer.start(timeout_ms)
        loop.exec()
        self._state_machine.entered.disconnect(_on_entered)
        timeout_timer.stop()
        timeout_timer.deleteLater()
        return completed["done"] and self.runtime_state.controller_state == target_state

    def _request_transition(self, state: ControllerState, *, overlay_text: str | None = None) -> bool:
        self._transition_request_token += 1
        request_token = self._transition_request_token
        # Invalidate any delayed overlay from earlier requests before this one.
        self._pending_overlay_token = request_token
        self._pending_overlay = None
        self._pending_overlay_state = None
        previous_state = self.runtime_state.controller_state
        # Invariant: transition requests must never pre-assign runtime state.
        # _on_controller_state_entered is the sole authority for state/timer/UI
        # side effects after an entered callback confirms completion.
        if previous_state == ControllerState.SAFE and state != ControllerState.SAFE:
            if self.runtime_state.fault_state == FaultState.SAFE and state != ControllerState.IDLE:
                return self._reject_transition_request(
                    requested_state=state,
                    previous_state=previous_state,
                    reason="safe_fault_gate",
                    token=request_token,
                )

        self._pending_overlay = overlay_text
        self._pending_overlay_state = state if overlay_text is not None else None
        self._pending_overlay_token = request_token
        # Audit P1.5: isolate transition confirmation from cycle-timer churn.
        restart_cycle_timer = self._cycle_timer.isActive()
        if restart_cycle_timer:
            self._cycle_timer.stop()
        self._transition_in_progress = True
        transition_requested = self._state_machine.request(state)
        if not transition_requested:
            LOGGER.debug("ignoring rejected transition requested=%s previous=%s", state.value, previous_state.value)
            self._transition_in_progress = False
            if restart_cycle_timer and self.runtime_state.controller_state in {
                ControllerState.REPLAY_RUNNING,
                ControllerState.LIVE_RUNNING,
            }:
                self._cycle_timer.start()
            return self._reject_transition_request(
                requested_state=state,
                previous_state=previous_state,
                reason="graph_rejected",
                token=request_token,
            )
        completed = self._wait_for_target_state(state)
        self._transition_in_progress = False
        if restart_cycle_timer and self.runtime_state.controller_state in {
            ControllerState.REPLAY_RUNNING,
            ControllerState.LIVE_RUNNING,
        }:
            self._cycle_timer.start()
        if not completed:
            return self._reject_transition_request(
                requested_state=state,
                previous_state=previous_state,
                reason="transition_not_completed",
                token=request_token,
            )
        self._set_transition_diagnostics(
            requested_state=state,
            previous_state=previous_state,
            result="accepted",
            reason="completed",
            token=request_token,
        )
        return True

    def _reject_transition_request(
        self,
        *,
        requested_state: ControllerState,
        previous_state: ControllerState,
        reason: str,
        token: int,
    ) -> bool:
        self._pending_overlay = None
        self._pending_overlay_state = None
        self._pending_overlay_token = self._transition_request_token
        self._set_transition_diagnostics(
            requested_state=requested_state,
            previous_state=previous_state,
            result="rejected",
            reason=reason,
            token=token,
        )
        LOGGER.debug(
            "transition rejected reason=%s requested=%s previous=%s current=%s diagnostics=%s",
            reason,
            requested_state.value,
            previous_state.value,
            self.runtime_state.controller_state.value,
            self._last_transition_diagnostics,
        )
        self._emit_runtime_state()
        return False

    def request_idle(self, *, overlay_text: str | None = None) -> bool:
        return self._request_transition(ControllerState.IDLE, overlay_text=overlay_text)

    def request_replay_mode(self) -> bool:
        return self._request_transition(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")

    def request_live_mode(self) -> bool:
        return self._request_transition(ControllerState.LIVE_RUNNING, overlay_text="Live mode active")

    def request_safe(self, *, overlay_text: str = "SAFE fault active") -> bool:
        return self._request_transition(ControllerState.SAFE, overlay_text=overlay_text)

    def _transition_to(self, state: ControllerState, *, overlay_text: str | None = None) -> bool:
        # Backward-compatible adapter for legacy callers.
        # runtime_state.controller_state must only be updated by
        # _on_controller_state_entered after an entered-state callback confirms
        # that the transition completed.
        return self._request_transition(state, overlay_text=overlay_text)

    @Slot()
    def _on_cycle_tick(self) -> None:
        if self._transition_in_progress:
            return
        if self.runtime_state.controller_state != ControllerState.REPLAY_RUNNING:
            return
        self._acquire_requests.put({"requested_at": time.monotonic()})
        deadline_s = time.monotonic() + (self.watchdog_config.cycle_budget_ms / 1000.0) + 0.05
        while time.monotonic() < deadline_s:
            if self._drain_ui_worker_events():
                return
            time.sleep(0.001)
        self._drain_ui_worker_events()

    def _drain_ui_worker_events(self) -> bool:
        observed_cycle_terminal_event = False
        while True:
            event = self._ui_event_queue.get(timeout_s=0.0)
            if event is None:
                return observed_cycle_terminal_event
            if not isinstance(event, _WorkerEvent):
                continue
            if event.kind == "source_fault":
                observed_cycle_terminal_event = True
                self._handle_source_fault(str(event.payload))
                continue
            if event.kind == "replay_complete":
                observed_cycle_terminal_event = True
                self._publish_session_evaluation()
                self._release_frame_source()
                self.runtime_state.scheduler_state = "IDLE"
                self.request_idle(overlay_text="Replay complete")
                continue
            if event.kind == "faulted":
                observed_cycle_terminal_event = True
                fault_state, detail = event.payload
                self.runtime_state.fault_state = fault_state
                self.runtime_state.scheduler_state = "IDLE"
                self._transition_to(ControllerState.FAULTED, overlay_text=detail)
                continue
            if event.kind != "cycle_complete":
                continue
            observed_cycle_terminal_event = True

            frame, logs, stage_ms, queue_stats = event.payload
            self.frame_preview_requested.emit(frame.tobytes(), frame.shape[1], frame.shape[0])
            self.window.statusBar().showMessage(
                " | ".join(
                    [
                        f"acq_q drop_oldest={queue_stats['request_q'].dropped_oldest}",
                        f"work_q drop_oldest={queue_stats['work_q'].dropped_oldest}",
                        f"ui_q drop_oldest={queue_stats['ui_q'].dropped_oldest}",
                        f"cycle_ms={stage_ms['cycle']:.1f}/{self.watchdog_config.cycle_budget_ms:.1f}",
                    ]
                )
            )

            for log_entry in logs:
                self._session_logs.append(log_entry)
                self.transport_response_received.emit(log_entry)
                self.log_entry_requested.emit(log_entry)

            if logs:
                self.runtime_state.previous_timestamp_s = logs[-1].frame_timestamp_s
            self.runtime_state.fault_state = self.transport.current_fault_state()
            if self.runtime_state.fault_state == FaultState.SAFE:
                self._set_protocol_mode(OperatorMode.SAFE)
                self.request_safe(overlay_text="SAFE fault active")
                return
            if self.runtime_state.fault_state == FaultState.WATCHDOG:
                self.runtime_state.scheduler_state = "IDLE"
                self._transition_to(ControllerState.FAULTED, overlay_text="Watchdog fault active")
                return
            self._emit_runtime_state()

    def _frame_worker_loop(self) -> None:
        while not self._worker_stop.is_set():
            request = self._acquire_requests.get(timeout_s=0.1)
            if request is None:
                continue
            try:
                started = time.perf_counter()
                frame = self._next_frame()
                if frame is None:
                    self._ui_event_queue.put(_WorkerEvent(kind="replay_complete", payload=None))
                    continue
                if not isinstance(frame.image_bgr, np.ndarray):
                    self._ui_event_queue.put(
                        _WorkerEvent(kind="faulted", payload=(FaultState.SAFE, "invalid frame type; expected numpy.ndarray"))
                    )
                    continue
                if frame.image_bgr.ndim != 3 or frame.image_bgr.shape[2] != 3:
                    self._ui_event_queue.put(
                        _WorkerEvent(kind="faulted", payload=(FaultState.SAFE, "invalid frame shape; expected (H,W,3)"))
                    )
                    continue
                if frame.image_bgr.dtype != np.uint8:
                    self._ui_event_queue.put(
                        _WorkerEvent(kind="faulted", payload=(FaultState.SAFE, "invalid frame dtype; expected uint8"))
                    )
                    continue
                frame_rgb = cv2.cvtColor(frame.image_bgr, cv2.COLOR_BGR2RGB)
                detections = tuple(self._detector.detect(frame.image_bgr))
                frame_stage_ms = (time.perf_counter() - started) * 1000.0
                if frame_stage_ms > self.watchdog_config.frame_acquire_detect_ms:
                    self._ui_event_queue.put(
                        _WorkerEvent(kind="faulted", payload=(FaultState.WATCHDOG, "acquire/detect watchdog exceeded"))
                    )
                    continue
                self._frame_transport_queue.put(
                    _DetectedFrameBatch(
                        frame=frame,
                        frame_rgb=frame_rgb,
                        detections=detections,
                        previous_timestamp_s=self.runtime_state.previous_timestamp_s,
                        stage_ms={"acquire_detect": frame_stage_ms},
                    )
                )
            except FrameSourceError as error:
                self._ui_event_queue.put(_WorkerEvent(kind="source_fault", payload=str(error)))
            except (DetectionError, cv2.error, TypeError, ValueError) as error:
                self._ui_event_queue.put(_WorkerEvent(kind="faulted", payload=(FaultState.SAFE, str(error))))
            except Exception as error:
                LOGGER.exception("frame_worker_unhandled_exception: %s", error)
                self._ui_event_queue.put(
                    _WorkerEvent(
                        kind="faulted",
                        payload=(
                            FaultState.SAFE,
                            "Frame processing encountered an unexpected error. Switched to SAFE mode.",
                        ),
                    )
                )

    def _transport_worker_loop(self) -> None:
        while not self._worker_stop.is_set():
            batch = self._frame_transport_queue.get(timeout_s=0.1)
            if batch is None or not isinstance(batch, _DetectedFrameBatch):
                continue
            decision_started = time.perf_counter()
            ordered_detections = tuple(sorted(batch.detections, key=lambda det: (batch.frame.timestamp_s, det.object_id)))
            if self._degraded_mode_active and self.runtime_state.operator_mode == OperatorMode.AUTO:
                logs = (
                    BenchLogEntry(
                        frame_timestamp_s=batch.frame.timestamp_s,
                        trigger_generation_s=batch.frame.timestamp_s,
                        lane=-1,
                        decision="autonomy_inhibited_degraded_camera",
                        record_type="operator_event",
                        rejection_reason="synthetic_or_unverified_camera",
                        protocol_round_trip_ms=0.0,
                        ack_code="-",
                        queue_depth=self._transport_queue_depth(),
                        scheduler_state=self.runtime_state.scheduler_state,
                        mode=GUI_TO_HOST_MODE[self.runtime_state.operator_mode],
                        command_source="degraded_guard",
                    ),
                )
            else:
                try:
                    logs = self.bench_runner.process_ingest_payload(
                        {
                            "frame_id": batch.frame.frame_id,
                            "timestamp": batch.frame.timestamp_s,
                            "image_shape": [batch.frame_rgb.shape[0], batch.frame_rgb.shape[1], batch.frame_rgb.shape[2]],
                            "detections": ordered_detections,
                            "previous_timestamp_s": batch.previous_timestamp_s,
                        }
                    )
                except SerialTransportError as error:
                    self._ui_event_queue.put(_WorkerEvent(kind="faulted", payload=(error.fault_state, error.detail)))
                    continue
            self._step_transport_queue()
            decision_transport_ms = (time.perf_counter() - decision_started) * 1000.0
            stage_ms = {
                "acquire_detect": batch.stage_ms["acquire_detect"],
                "decision_transport": decision_transport_ms,
                "cycle": batch.stage_ms["acquire_detect"] + decision_transport_ms,
            }
            if decision_transport_ms > self.watchdog_config.transport_ms or stage_ms["cycle"] > self.watchdog_config.cycle_budget_ms:
                self._ui_event_queue.put(
                    _WorkerEvent(kind="faulted", payload=(FaultState.WATCHDOG, "cycle budget exceeded before command emit"))
                )
                continue
            queue_stats = {
                "request_q": self._acquire_requests.metrics,
                "work_q": self._frame_transport_queue.metrics,
                "ui_q": self._ui_event_queue.metrics,
            }
            self._ui_event_queue.put(_WorkerEvent(kind="cycle_complete", payload=(batch.frame_rgb, logs, stage_ms, queue_stats)))

    def _clear_worker_backlog(self) -> None:
        while self._acquire_requests.get(timeout_s=0.0) is not None:
            pass
        while self._frame_transport_queue.get(timeout_s=0.0) is not None:
            pass
        while self._ui_event_queue.get(timeout_s=0.0) is not None:
            pass

    def _next_frame(self):
        if (
            self.runtime_state.mode == BenchMode.REPLAY
            and self._selected_transport_kind == "mock"
            and self._simulated_overlay_enabled
        ):
            return self._build_simulated_frame()
        # Temporary POC simplification: if no camera is available in LIVE mode,
        # generate synthetic frames so the GUI and protocol path stay testable.
        if self._use_simulated_live_feed:
            return self._build_simulated_frame()
        if self._frame_source is None:
            return None
        return self._frame_source.next_frame()

    def _build_simulated_frame(self) -> BenchFrame:
        height, width = 480, 640
        image_bgr = np.zeros((height, width, 3), dtype=np.uint8)
        x = 40 + (self._simulated_frame_id * 12) % (width - 80)
        cv2.circle(image_bgr, (x, height // 2), 26, (0, 255, 255), -1)
        timestamp_s = self._simulated_frame_id * self.live_config.frame_period_s
        frame = BenchFrame(frame_id=self._simulated_frame_id, timestamp_s=timestamp_s, image_bgr=image_bgr)
        self._simulated_frame_id += 1
        return frame

    def _release_frame_source(self) -> None:
        if self._frame_source is not None:
            self._frame_source.release()
            self._frame_source = None

    def _activate_frame_source(self, mode: BenchMode) -> bool:
        self._release_frame_source()
        self._use_simulated_live_feed = False
        source: BenchFrameSource = self.replay_source if mode == BenchMode.REPLAY else LiveFrameSource(self.live_config)
        try:
            source.open()
        except FrameSourceError as error:
            if mode == BenchMode.LIVE:
                if not self._operator_acknowledges_simulated_feed(str(error)):
                    self._handle_source_fault("LIVE camera unavailable; simulated feed not acknowledged")
                    return False
                self._use_simulated_live_feed = True
                self._simulated_frame_id = 0
                self._set_degraded_mode(True, "Synthetic camera feed in LIVE mode")
                return True
            self._handle_source_fault(str(error))
            return False
        self._frame_source = source
        self._set_degraded_mode(False)
        return True

    def _operator_acknowledges_simulated_feed(self, detail: str) -> bool:
        if not self._allow_blocking_live_prompt:
            LOGGER.info(
                "non-blocking live startup prompt gate active; simulated feed not auto-acknowledged detail=%s",
                detail,
            )
            return False
        response = QMessageBox.question(
            self.window,
            "Acknowledge simulated feed",
            f"LIVE camera unavailable ({detail}). Use simulated feed and enter degraded mode?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return response == QMessageBox.StandardButton.Yes

    def _handle_source_fault(self, message: str) -> None:
        self._release_frame_source()
        self.runtime_state.fault_state = FaultState.WATCHDOG
        self.runtime_state.scheduler_state = "IDLE"
        self._transition_to(ControllerState.FAULTED, overlay_text=message)
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=self.runtime_state.previous_timestamp_s,
                trigger_generation_s=0.0,
                lane=-1,
                decision=f"source_fault: {message}",
                rejection_reason="frame_source_error",
                protocol_round_trip_ms=0.0,
                ack_code="-",
            )
        )

    def _step_transport_queue(self) -> None:
        if not isinstance(self.transport, MockMcuTransport):
            return
        if self.cycle_config.queue_consumption_policy == QueueConsumptionPolicy.NONE:
            self.transport.step_queue(items_to_consume=0)
            return
        if self.cycle_config.queue_consumption_policy == QueueConsumptionPolicy.ALL:
            self.transport.step_queue(items_to_consume=len(self.transport.queue))
            return
        self.transport.step_queue(items_to_consume=1)

    def _send_protocol_command(self, command: str, args: tuple[object, ...] = ()) -> AckResponse | None:
        if hasattr(self.transport, "send_command"):
            sender = getattr(self.transport, "send_command")
            if callable(sender):
                ack = sender(command, args)
                if isinstance(ack, AckResponse):
                    return ack

        response_frame = self._protocol_host.handle_frame(serialize_packet(command, args))
        parsed_response = parse_frame(response_frame)
        return parse_ack_tokens((parsed_response.command, *parsed_response.args))

    def _send_poc_fire_command(self, reason: str) -> AckResponse | None:
        if reason != "manual_fire_test":
            self._set_last_command_status("manual fire rejected: manual-test path only")
            return None
        if self.runtime_state.operator_mode != OperatorMode.MANUAL:
            self._set_last_command_status("manual fire rejected: requires MANUAL mode")
            return None

        lane = int(self.window.manual_lane_input.value())
        position_mm = float(self.window.manual_position_input.value())
        manual_cfg = self._runtime_config.bench_gui.manual_servo
        raw_text = str(self.window.manual_position_input.lineEdit().text()).strip()
        try:
            raw_position_mm = float(raw_text)
        except ValueError:
            self._set_last_command_status(f"manual fire rejected: position '{raw_text}' is not a number")
            return None
        if lane not in range(manual_cfg.min_lane, manual_cfg.max_lane + 1):
            self._set_last_command_status(f"manual fire rejected: lane {lane} out of range")
            return None
        if raw_position_mm < manual_cfg.min_position_mm or raw_position_mm > manual_cfg.max_position_mm:
            self._set_last_command_status(f"manual fire rejected: position {raw_position_mm} out of range")
            return None

        response = self.transport.send(ScheduledCommand(lane=lane, position_mm=position_mm))
        ack = AckResponse(
            status="ACK" if response.ack_code == AckCode.ACK else "NACK",
            nack_code=response.nack_code,
            detail=response.nack_detail,
            queue_depth=response.queue_depth,
            scheduler_state=response.scheduler_state,
            mode=response.mode,
            queue_cleared=response.queue_cleared,
        )
        self._update_transport_queue_observation(response.queue_depth, response.queue_cleared)
        self.runtime_state.scheduler_state = response.scheduler_state
        detail = "ACK" if ack.status == "ACK" else f"NACK({ack.nack_code})"
        self._set_last_command_status(f"<SCHED|{lane}|{position_mm:.1f}> ({reason}) -> {detail}")
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=self.runtime_state.previous_timestamp_s,
                trigger_generation_s=self.runtime_state.previous_timestamp_s,
                lane=lane,
                decision="manual_fire_test",
                record_type="operator_event",
                rejection_reason=None,
                protocol_round_trip_ms=response.round_trip_ms,
                ack_code=ack.status,
                queue_depth=response.queue_depth,
                scheduler_state=response.scheduler_state,
                mode=response.mode,
                queue_cleared=response.queue_cleared,
                command_source="manual_test",
            )
        )
        self._emit_runtime_state()
        return ack

    def _reset_protocol_queue(self) -> AckResponse | None:
        ack = self._send_protocol_command("RESET_QUEUE")
        if ack is None or ack.status != "ACK":
            return None
        self._update_transport_queue_observation(ack.queue_depth, ack.queue_cleared)
        self.runtime_state.scheduler_state = ack.scheduler_state or "IDLE"
        self._transport_clear_queue() if ack.queue_cleared else None
        return ack

    def _publish_session_evaluation(self) -> None:
        evaluation = evaluate_logs(tuple(self._session_logs), self._selected_scenarios)
        result_line = "; ".join(f"{result.name}:{'PASS' if result.passed else 'FAIL'}" for result in evaluation.scenarios)
        self.lane_overlay_requested.emit(f"Scenario result {result_line} | overall={'PASS' if evaluation.passed else 'FAIL'}")
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=self.runtime_state.previous_timestamp_s,
                trigger_generation_s=self.runtime_state.previous_timestamp_s,
                lane=-1,
                decision=f"scenario_eval overall={'PASS' if evaluation.passed else 'FAIL'}",
                record_type="operator_event",
                rejection_reason=result_line,
                protocol_round_trip_ms=float(evaluation.summary["avg_round_trip_ms"]),
                ack_code="-",
            )
        )

    def _set_protocol_mode(self, target_mode: OperatorMode):
        if not self._is_mode_transition_allowed(self.runtime_state.operator_mode, target_mode):
            return None
        wanted_mode = GUI_TO_HOST_MODE[target_mode]
        ack = self._send_protocol_command("SET_MODE", (wanted_mode,))
        if ack is None:
            return None
        if ack.status != "ACK":
            return None
        self._update_transport_queue_observation(ack.queue_depth, ack.queue_cleared)
        self._set_operator_mode(target_mode)
        self.runtime_state.scheduler_state = ack.scheduler_state
        self._apply_protocol_queue_side_effects(ack.queue_cleared)
        return ack

    def _update_transport_queue_observation(self, depth: object, queue_cleared: object) -> None:
        if isinstance(depth, int) and depth >= 0:
            self._latest_transport_queue_depth = depth
        self._latest_transport_queue_cleared_seq += 1
        self._latest_transport_queue_cleared = bool(queue_cleared)

    @staticmethod
    def _is_mode_transition_allowed(current_mode: OperatorMode, target_mode: OperatorMode) -> bool:
        return is_mode_transition_allowed(GUI_TO_HOST_MODE[current_mode], GUI_TO_HOST_MODE[target_mode])

    def recover_safe_to_manual(self) -> bool:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self.runtime_state.fault_state != FaultState.SAFE:
            self._audit_operator_command("recover_safe_to_manual", outcome="rejected_not_safe", before_mode=before_mode, queue_before=queue_before)
            return False
        if not self._is_mode_transition_allowed(self.runtime_state.operator_mode, OperatorMode.MANUAL):
            self._audit_operator_command("recover_safe_to_manual", outcome="rejected_transition", before_mode=before_mode, queue_before=queue_before)
            return False
        ack = self._set_protocol_mode(OperatorMode.MANUAL)
        if ack is None:
            self._audit_operator_command("recover_safe_to_manual", outcome="nack", before_mode=before_mode, queue_before=queue_before)
            return False
        self.runtime_state.fault_state = FaultState.NORMAL
        self.request_idle(overlay_text="SAFE cleared; MANUAL mode")
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=self.runtime_state.previous_timestamp_s,
                trigger_generation_s=self.runtime_state.previous_timestamp_s,
                lane=-1,
                decision="safe_recovery_manual",
                record_type="operator_event",
                rejection_reason=None,
                protocol_round_trip_ms=0.0,
                ack_code="-",
            )
        )
        self._audit_operator_command("recover_safe_to_manual", outcome="processed", before_mode=before_mode, queue_before=queue_before)
        return True

    def recover_to_auto(self) -> bool:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self.runtime_state.controller_state != ControllerState.IDLE:
            self._audit_operator_command("recover_to_auto", outcome="rejected_non_idle", before_mode=before_mode, queue_before=queue_before)
            return False
        if not self._is_mode_transition_allowed(self.runtime_state.operator_mode, OperatorMode.AUTO):
            self._audit_operator_command("recover_to_auto", outcome="rejected_transition", before_mode=before_mode, queue_before=queue_before)
            return False
        ack = self._set_protocol_mode(OperatorMode.AUTO)
        if ack is None:
            self._audit_operator_command("recover_to_auto", outcome="nack", before_mode=before_mode, queue_before=queue_before)
            return False
        self.runtime_state.fault_state = FaultState.NORMAL
        self.request_idle(overlay_text="AUTO mode active")
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=self.runtime_state.previous_timestamp_s,
                trigger_generation_s=self.runtime_state.previous_timestamp_s,
                lane=-1,
                decision="mode_auto",
                record_type="operator_event",
                rejection_reason=None,
                protocol_round_trip_ms=0.0,
                ack_code="-",
            )
        )
        self._audit_operator_command("recover_to_auto", outcome="processed", before_mode=before_mode, queue_before=queue_before)
        return True

    def _transport_queue_depth(self) -> int:
        return self._latest_transport_queue_depth

    def _transport_clear_queue(self) -> None:
        if isinstance(self.transport, MockMcuTransport):
            self.transport.queue.clear()

    def _transport_last_queue_cleared(self) -> bool:
        if self._latest_transport_queue_cleared_seq > 0:
            return self._latest_transport_queue_cleared
        for accessor_name in ("transport_last_queue_cleared", "last_queue_cleared_observation"):
            if hasattr(self.transport, accessor_name):
                accessor = getattr(self.transport, accessor_name)
                if callable(accessor):
                    observed = accessor()
                    if isinstance(observed, bool):
                        if observed:
                            self._latest_transport_queue_cleared = True
                            self._latest_transport_queue_cleared_seq += 1
                            return True
                        return False
        return self._latest_transport_queue_cleared

    def _apply_protocol_queue_side_effects(self, queue_cleared: bool) -> None:
        if queue_cleared or self._transport_last_queue_cleared():
            self._transport_clear_queue()

    @Slot()
    def on_replay_clicked(self) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self.runtime_state.controller_state != ControllerState.IDLE:
            self._audit_operator_command("replay", outcome="ignored_non_idle", before_mode=before_mode, queue_before=queue_before)
            return
        self.runtime_state.mode = BenchMode.REPLAY
        self._session_logs.clear()
        self._clear_worker_backlog()
        if not self._activate_frame_source(BenchMode.REPLAY):
            self._audit_operator_command("replay", outcome="source_activation_failed", before_mode=before_mode, queue_before=queue_before)
            return
        self.request_replay_mode()
        self._audit_operator_command("replay", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot()
    def on_live_clicked(self) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self.runtime_state.controller_state != ControllerState.IDLE:
            self._audit_operator_command("live", outcome="ignored_non_idle", before_mode=before_mode, queue_before=queue_before)
            return
        self.runtime_state.mode = BenchMode.LIVE
        self._session_logs.clear()
        self._clear_worker_backlog()
        if not self._activate_frame_source(BenchMode.LIVE):
            self._audit_operator_command("live", outcome="source_activation_failed", before_mode=before_mode, queue_before=queue_before)
            return
        self.request_live_mode()
        self._audit_operator_command("live", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot()
    def on_home_clicked(self) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self.runtime_state.controller_state == ControllerState.SAFE:
            self.recover_safe_to_manual()
            self._audit_operator_command("home", outcome="safe_recovery", before_mode=before_mode, queue_before=queue_before)
            return
        if self.runtime_state.controller_state in {ControllerState.REPLAY_RUNNING, ControllerState.LIVE_RUNNING}:
            self._publish_session_evaluation()
        self._cycle_timer.stop()
        self._clear_worker_backlog()
        self._reset_protocol_queue()
        self._release_frame_source()
        self.runtime_state.previous_timestamp_s = 0.0
        self.runtime_state.fault_state = FaultState.NORMAL
        self.runtime_state.scheduler_state = "IDLE"
        self.request_idle(overlay_text="Homing complete")
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=0.0,
                trigger_generation_s=0.0,
                lane=-1,
                decision="home",
                record_type="operator_event",
                rejection_reason=None,
                protocol_round_trip_ms=0.0,
                ack_code="-",
            )
        )
        self._audit_operator_command("home", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot(float)
    def on_trigger_threshold_changed(self, value: float) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        self.trigger_threshold = value
        self._audit_operator_command("trigger_threshold", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot(float)
    def on_belt_speed_changed(self, value: float) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        self.belt_speed_mm_s = value
        self._audit_operator_command("belt_speed", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot(str)
    def on_mcu_selector_changed(self, value: str) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self._is_auto_cycle_active():
            self._audit_operator_command("mcu_selector", outcome="blocked_auto_cycle", before_mode=before_mode, queue_before=queue_before)
            return
        self._selected_transport_kind = value
        self._audit_operator_command("mcu_selector", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot(str)
    def on_com_selector_changed(self, value: str) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self._is_auto_cycle_active():
            self._audit_operator_command("com_selector", outcome="blocked_auto_cycle", before_mode=before_mode, queue_before=queue_before)
            return
        self._selected_serial_port = value
        self._audit_operator_command("com_selector", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot(str)
    def on_baud_selector_changed(self, value: str) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self._is_auto_cycle_active():
            self._audit_operator_command("baud_selector", outcome="blocked_auto_cycle", before_mode=before_mode, queue_before=queue_before)
            return
        try:
            self._selected_serial_baud = int(value)
        except ValueError:
            self._audit_operator_command("baud_selector", outcome="invalid_value", before_mode=before_mode, queue_before=queue_before)
            return
        self._audit_operator_command("baud_selector", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot(str)
    def on_log_level_changed(self, value: str) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        self._selected_log_level = value
        self._audit_operator_command("log_level", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot()
    def on_clear_log_clicked(self) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        self.window.log_table.setRowCount(0)
        self._audit_operator_command("clear_log", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot()
    def on_fire_test_clicked(self) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self._is_auto_cycle_active():
            self._set_last_command_status("manual fire rejected: AUTO cycle active")
            self._audit_operator_command("fire_test", outcome="blocked_auto_cycle", before_mode=before_mode, queue_before=queue_before)
            return
        self._send_poc_fire_command(reason="manual_fire_test")
        self._audit_operator_command("fire_test", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    @Slot()
    def on_serial_connect_clicked(self) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self._is_auto_cycle_active():
            self._set_serial_status(self._serial_connected, "blocked: AUTO cycle active")
            self._audit_operator_command("serial_connect", outcome="blocked_auto_cycle", before_mode=before_mode, queue_before=queue_before)
            return
        selected_kind = self._selected_transport_kind
        if selected_kind == "mock":
            self.transport = MockMcuTransport(
                config=MockTransportConfig(
                    max_queue_depth=self.transport_config.max_queue_depth,
                    base_round_trip_ms=self.transport_config.base_round_trip_ms,
                    per_item_penalty_ms=self.transport_config.per_item_penalty_ms,
                )
            )
            self._serial_connected = False
            self._set_serial_status(False, "mock transport")
            self._audit_operator_command("serial_connect", outcome="processed", before_mode=before_mode, queue_before=queue_before)
            return

        if self._serial_connected:
            self._set_serial_status(True)
            self._audit_operator_command("serial_connect", outcome="already_connected", before_mode=before_mode, queue_before=queue_before)
            return
        try:
            transport_cls = SerialMcuTransport if selected_kind == "serial" else Esp32McuTransport
            selected_port = self.window.com_selector.currentText()
            selected_baud = int(self.window.baud_selector.currentText())
            self._selected_serial_port = selected_port
            self._selected_serial_baud = selected_baud
            self.transport = transport_cls(
                config=SerialTransportConfig(
                    port=selected_port,
                    baud=selected_baud,
                    timeout_s=self._runtime_config.transport.serial_timeout_s,
                )
            )
            self._serial_connected = True
            self._set_serial_status(True)
            self._audit_operator_command("serial_connect", outcome="processed", before_mode=before_mode, queue_before=queue_before)
        except RuntimeError as exc:
            self._set_serial_status(False, self._serial_connect_error_detail(exc))
            self._audit_operator_command("serial_connect", outcome="error", before_mode=before_mode, queue_before=queue_before)

    @Slot()
    def on_serial_disconnect_clicked(self) -> None:
        before_mode = self.runtime_state.operator_mode
        queue_before = self._capture_queue_state()
        if self._is_auto_cycle_active():
            self._set_serial_status(self._serial_connected, "blocked: AUTO cycle active")
            self._audit_operator_command("serial_disconnect", outcome="blocked_auto_cycle", before_mode=before_mode, queue_before=queue_before)
            return
        if hasattr(self.transport, "close") and callable(self.transport.close):
            self.transport.close()
        self._serial_connected = False
        self._set_serial_status(False)
        self._audit_operator_command("serial_disconnect", outcome="processed", before_mode=before_mode, queue_before=queue_before)

    def _serial_connect_error_detail(self, error: RuntimeError) -> str:
        error_text = str(error)
        if "pyserial is required" in error_text:
            return "pyserial missing; install with: python -m pip install -e .[serial]"
        return error_text
