from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import cv2
from PySide6.QtCore import QObject, QState, QStateMachine, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from coloursorter.bench import (
    BenchFrameSource,
    BenchLogEntry,
    BenchMode,
    BenchRunner,
    EncoderConfig,
    FaultState,
    FrameSourceError,
    LiveConfig,
    LiveFrameSource,
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
from coloursorter.deploy import OpenCvDetectionProvider, PipelineRunner
from coloursorter.protocol import OpenSpecV3Host, is_mode_transition_allowed
from coloursorter.serial_interface import AckResponse, parse_ack_tokens, parse_frame, serialize_packet

from .app import BenchMainWindow, QueueState


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


@dataclass
class BenchRuntimeState:
    mode: BenchMode
    previous_timestamp_s: float
    fault_state: FaultState
    controller_state: ControllerState
    operator_mode: OperatorMode
    scheduler_state: str = "IDLE"


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


class BenchAppController(QObject):
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
        self.window = BenchMainWindow()

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
        self.runtime_state = BenchRuntimeState(
            mode=BenchMode(runtime_config.frame_source.mode),
            previous_timestamp_s=0.0,
            fault_state=FaultState.NORMAL,
            controller_state=ControllerState.IDLE,
            operator_mode=OperatorMode.AUTO,
        )
        self.cycle_config = BenchCycleConfig(
            period_ms=runtime_config.cycle_timing.period_ms,
            queue_consumption_policy=QueueConsumptionPolicy(runtime_config.cycle_timing.queue_consumption_policy),
        )

        project_root = Path(__file__).resolve().parents[2]
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
        if runtime_config.transport.kind == "serial":
            self.transport = SerialMcuTransport(
                config=SerialTransportConfig(
                    port=runtime_config.transport.serial_port,
                    baud=runtime_config.transport.serial_baud,
                    timeout_s=runtime_config.transport.serial_timeout_s,
                )
            )
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
        self._selected_scenarios = tuple(
            s for s in scenarios_from_thresholds(runtime_config.scenario_thresholds) if s.name == "nominal"
        )
        self._session_logs: list[BenchLogEntry] = []
        self._frame_source: BenchFrameSource | None = None
        self._latest_transport_queue_depth = 0
        self._latest_transport_queue_cleared = False
        self._cycle_timer = QTimer(self)
        self._cycle_timer.setInterval(self.cycle_config.period_ms)
        self._cycle_timer.timeout.connect(self._on_cycle_tick)

        self._state_machine = BenchControllerStateMachine(self)
        self._state_machine.entered.connect(self._on_controller_state_entered)

        self._connect_view_actions()
        self._connect_view_updates()
        self.mode_changed.connect(self._on_mode_changed)
        self.transport_response_received.connect(self._on_transport_response_received)
        self._on_controller_state_entered(ControllerState.IDLE)

    def start(self) -> int:
        self.window.resize(1200, 900)
        self.window.show()
        return self._app.exec()

    def _connect_view_actions(self) -> None:
        self.window.replay_button.clicked.connect(self.on_replay_clicked)
        self.window.live_button.clicked.connect(self.on_live_clicked)
        self.window.home_button.clicked.connect(self.on_home_clicked)

    def _connect_view_updates(self) -> None:
        self.frame_preview_requested.connect(self.window.update_frame_preview)
        self.lane_overlay_requested.connect(self.window.set_lane_overlay)
        self.queue_state_requested.connect(self.window.set_queue_state)
        self.fault_state_requested.connect(self.window.set_fault_state)
        self.log_entry_requested.connect(self.window.append_log_entry)

    def _emit_runtime_state(self) -> None:
        self.queue_state_requested.emit(
            QueueState(
                depth=self._transport_queue_depth(),
                capacity=self.transport_config.max_queue_depth,
                controller_state=self.runtime_state.controller_state.value,
                scheduler_state=self.runtime_state.scheduler_state,
                mode=GUI_TO_HOST_MODE[self.runtime_state.operator_mode],
            )
        )
        self.fault_state_requested.emit(self.runtime_state.fault_state)

    def _on_controller_state_entered(self, state: ControllerState) -> None:
        self.runtime_state.controller_state = state
        running = state in {ControllerState.REPLAY_RUNNING, ControllerState.LIVE_RUNNING}
        if running and not self._cycle_timer.isActive():
            self._cycle_timer.start()
        if not running and self._cycle_timer.isActive():
            self._cycle_timer.stop()

        self._update_buttons_for_controller_state(state)
        self._update_buttons_for_mode(self.runtime_state.operator_mode)
        self._emit_runtime_state()

    @Slot(object)
    def _on_mode_changed(self, mode: OperatorMode) -> None:
        self._update_buttons_for_mode(mode)
        self._emit_runtime_state()

    @Slot(object)
    def _on_transport_response_received(self, log_entry: BenchLogEntry) -> None:
        self._latest_transport_queue_depth = max(0, int(log_entry.queue_depth))
        self._latest_transport_queue_cleared = bool(log_entry.queue_cleared)
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
        self.window.replay_button.setEnabled(state == ControllerState.IDLE)
        self.window.live_button.setEnabled(state == ControllerState.IDLE)
        self.window.home_button.setEnabled(state != ControllerState.FAULTED)

    def _update_buttons_for_mode(self, mode: OperatorMode) -> None:
        if mode == OperatorMode.SAFE:
            self.window.home_button.setText("Clear SAFE")
        else:
            self.window.home_button.setText("Home")

    def _transition_to(self, state: ControllerState, *, overlay_text: str | None = None) -> None:
        if state == self.runtime_state.controller_state:
            if overlay_text is not None:
                self.lane_overlay_requested.emit(overlay_text)
            self._emit_runtime_state()
            return
        if state == ControllerState.REPLAY_RUNNING:
            self._state_machine.start_replay.emit()
        elif state == ControllerState.LIVE_RUNNING:
            self._state_machine.start_live.emit()
        elif state == ControllerState.IDLE:
            self._state_machine.go_idle.emit()
        elif state == ControllerState.FAULTED:
            self._state_machine.set_faulted.emit()
        elif state == ControllerState.SAFE:
            self._state_machine.set_safe.emit()
        if overlay_text is not None:
            self.lane_overlay_requested.emit(overlay_text)

    @Slot()
    def _on_cycle_tick(self) -> None:
        if self.runtime_state.controller_state not in {ControllerState.REPLAY_RUNNING, ControllerState.LIVE_RUNNING}:
            return

        try:
            frame = self._next_frame()
        except FrameSourceError as error:
            self._handle_source_fault(str(error))
            return

        if frame is None:
            self._publish_session_evaluation()
            self._release_frame_source()
            self.runtime_state.scheduler_state = "IDLE"
            self._transition_to(ControllerState.IDLE, overlay_text="Replay complete")
            return

        frame_rgb = cv2.cvtColor(frame.image_bgr, cv2.COLOR_BGR2RGB)
        self.frame_preview_requested.emit(frame_rgb.tobytes(), frame_rgb.shape[1], frame_rgb.shape[0])

        detections = self._detector.detect(frame.image_bgr)
        try:
            logs = self.bench_runner.run_cycle(
                frame_id=frame.frame_id,
                timestamp_s=frame.timestamp_s,
                image_height_px=frame_rgb.shape[0],
                image_width_px=frame_rgb.shape[1],
                detections=detections,
                previous_timestamp_s=self.runtime_state.previous_timestamp_s,
            )
        except SerialTransportError as error:
            self.runtime_state.fault_state = error.fault_state
            self.runtime_state.scheduler_state = "IDLE"
            self._transition_to(ControllerState.FAULTED, overlay_text=error.detail)
            return
        self._step_transport_queue()

        for log_entry in logs:
            self._session_logs.append(log_entry)
            self.transport_response_received.emit(log_entry)
            self.log_entry_requested.emit(log_entry)

        self.runtime_state.previous_timestamp_s = frame.timestamp_s
        self.runtime_state.fault_state = self.transport.current_fault_state()

        if self.runtime_state.fault_state == FaultState.SAFE:
            self._set_protocol_mode(OperatorMode.SAFE)
            self._transition_to(ControllerState.SAFE, overlay_text="SAFE fault active")
            return
        if self.runtime_state.fault_state == FaultState.WATCHDOG:
            self.runtime_state.scheduler_state = "IDLE"
            self._transition_to(ControllerState.FAULTED, overlay_text="Watchdog fault active")
            return
        self._emit_runtime_state()

    def _next_frame(self):
        if self._frame_source is None:
            return None
        return self._frame_source.next_frame()

    def _release_frame_source(self) -> None:
        if self._frame_source is not None:
            self._frame_source.release()
            self._frame_source = None

    def _activate_frame_source(self, mode: BenchMode) -> bool:
        self._release_frame_source()
        source: BenchFrameSource = self.replay_source if mode == BenchMode.REPLAY else LiveFrameSource(self.live_config)
        try:
            source.open()
        except FrameSourceError as error:
            self._handle_source_fault(str(error))
            return False
        self._frame_source = source
        return True

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

    def _reset_protocol_queue(self) -> AckResponse | None:
        ack = self._send_protocol_command("RESET_QUEUE")
        if ack is None or ack.status != "ACK":
            return None
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
        self._set_operator_mode(target_mode)
        self.runtime_state.scheduler_state = ack.scheduler_state
        self._apply_protocol_queue_side_effects(ack.queue_cleared)
        return ack

    @staticmethod
    def _is_mode_transition_allowed(current_mode: OperatorMode, target_mode: OperatorMode) -> bool:
        return is_mode_transition_allowed(GUI_TO_HOST_MODE[current_mode], GUI_TO_HOST_MODE[target_mode])

    def recover_safe_to_manual(self) -> bool:
        if self.runtime_state.controller_state != ControllerState.SAFE:
            return False
        if not self._is_mode_transition_allowed(self.runtime_state.operator_mode, OperatorMode.MANUAL):
            return False
        ack = self._set_protocol_mode(OperatorMode.MANUAL)
        if ack is None:
            return False
        self.runtime_state.fault_state = FaultState.NORMAL
        self._transition_to(ControllerState.IDLE, overlay_text="SAFE cleared; MANUAL mode")
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=self.runtime_state.previous_timestamp_s,
                trigger_generation_s=self.runtime_state.previous_timestamp_s,
                lane=-1,
                decision="safe_recovery_manual",
                rejection_reason=None,
                protocol_round_trip_ms=0.0,
                ack_code="-",
            )
        )
        return True

    def recover_to_auto(self) -> bool:
        if self.runtime_state.controller_state != ControllerState.IDLE:
            return False
        if not self._is_mode_transition_allowed(self.runtime_state.operator_mode, OperatorMode.AUTO):
            return False
        ack = self._set_protocol_mode(OperatorMode.AUTO)
        if ack is None:
            return False
        self.runtime_state.fault_state = FaultState.NORMAL
        self._transition_to(ControllerState.IDLE, overlay_text="AUTO mode active")
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=self.runtime_state.previous_timestamp_s,
                trigger_generation_s=self.runtime_state.previous_timestamp_s,
                lane=-1,
                decision="mode_auto",
                rejection_reason=None,
                protocol_round_trip_ms=0.0,
                ack_code="-",
            )
        )
        return True

    def _transport_queue_depth(self) -> int:
        if hasattr(self.transport, "current_queue_depth"):
            depth = self.transport.current_queue_depth()
            if isinstance(depth, int) and depth >= 0:
                self._latest_transport_queue_depth = depth
                return depth
        return self._latest_transport_queue_depth

    def _transport_clear_queue(self) -> None:
        if isinstance(self.transport, MockMcuTransport):
            self.transport.queue.clear()

    def _transport_last_queue_cleared(self) -> bool:
        if hasattr(self.transport, "last_queue_cleared_observation"):
            observed = self.transport.last_queue_cleared_observation()
            if isinstance(observed, bool):
                self._latest_transport_queue_cleared = observed
                return observed
        return self._latest_transport_queue_cleared

    def _apply_protocol_queue_side_effects(self, queue_cleared: bool) -> None:
        if queue_cleared or self._transport_last_queue_cleared():
            self._transport_clear_queue()

    @Slot()
    def on_replay_clicked(self) -> None:
        if self.runtime_state.controller_state != ControllerState.IDLE:
            return
        self.runtime_state.mode = BenchMode.REPLAY
        self._session_logs.clear()
        if not self._activate_frame_source(BenchMode.REPLAY):
            return
        self._transition_to(ControllerState.REPLAY_RUNNING, overlay_text="Replay mode active")

    @Slot()
    def on_live_clicked(self) -> None:
        if self.runtime_state.controller_state != ControllerState.IDLE:
            return
        self.runtime_state.mode = BenchMode.LIVE
        self._session_logs.clear()
        if not self._activate_frame_source(BenchMode.LIVE):
            return
        self._transition_to(ControllerState.LIVE_RUNNING, overlay_text="Live mode active")

    @Slot()
    def on_home_clicked(self) -> None:
        if self.runtime_state.controller_state == ControllerState.SAFE:
            self.recover_safe_to_manual()
            return
        if self.runtime_state.controller_state in {ControllerState.REPLAY_RUNNING, ControllerState.LIVE_RUNNING}:
            self._publish_session_evaluation()
        self._cycle_timer.stop()
        self._reset_protocol_queue()
        self._release_frame_source()
        self.runtime_state.previous_timestamp_s = 0.0
        self.runtime_state.fault_state = FaultState.NORMAL
        self.runtime_state.scheduler_state = "IDLE"
        self._transition_to(ControllerState.IDLE, overlay_text="Homing complete")
        self.log_entry_requested.emit(
            BenchLogEntry(
                frame_timestamp_s=0.0,
                trigger_generation_s=0.0,
                lane=-1,
                decision="home",
                rejection_reason=None,
                protocol_round_trip_ms=0.0,
                ack_code="-",
            )
        )
