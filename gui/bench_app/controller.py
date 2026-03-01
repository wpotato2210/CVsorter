from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import cv2
from PySide6.QtCore import QObject, QTimer, Signal, Slot
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
from coloursorter.bench.serial_transport import (
    SerialMcuTransport,
    SerialTransportConfig,
    SerialTransportError,
)
from coloursorter.config import RuntimeConfig
from coloursorter.deploy import OpenCvDetectionProvider, PipelineRunner
from coloursorter.protocol import OpenSpecV3Host, is_mode_transition_allowed
from coloursorter.serial_interface import parse_ack_tokens, parse_frame, serialize_packet

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


@dataclass
class BenchRuntimeState:
    mode: BenchMode
    previous_timestamp_s: float
    fault_state: FaultState
    controller_state: ControllerState
    operator_mode: OperatorMode


class BenchAppController(QObject):
    frame_preview_requested = Signal(bytes, int, int)
    lane_overlay_requested = Signal(str)
    queue_state_requested = Signal(object)
    fault_state_requested = Signal(object)
    log_entry_requested = Signal(object)

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
        self._selected_scenarios = tuple(s for s in scenarios_from_thresholds(runtime_config.scenario_thresholds) if s.name == "nominal")
        self._session_logs: list[BenchLogEntry] = []
        self._frame_source: BenchFrameSource | None = None
        self._cycle_timer = QTimer(self)
        self._cycle_timer.setInterval(self.cycle_config.period_ms)
        self._cycle_timer.timeout.connect(self._on_cycle_tick)

        self._connect_view_actions()
        self._connect_view_updates()
        self._transition_to(ControllerState.IDLE)

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
                state=self.runtime_state.controller_state.value,
            )
        )
        self.fault_state_requested.emit(self.runtime_state.fault_state)

    def _transition_to(self, state: ControllerState, *, overlay_text: str | None = None) -> None:
        legal = {
            ControllerState.IDLE: {
                ControllerState.IDLE,
                ControllerState.REPLAY_RUNNING,
                ControllerState.LIVE_RUNNING,
                ControllerState.FAULTED,
                ControllerState.SAFE,
            },
            ControllerState.REPLAY_RUNNING: {
                ControllerState.IDLE,
                ControllerState.REPLAY_RUNNING,
                ControllerState.FAULTED,
                ControllerState.SAFE,
            },
            ControllerState.LIVE_RUNNING: {
                ControllerState.IDLE,
                ControllerState.LIVE_RUNNING,
                ControllerState.FAULTED,
                ControllerState.SAFE,
            },
            ControllerState.FAULTED: {ControllerState.IDLE, ControllerState.SAFE},
            ControllerState.SAFE: {ControllerState.IDLE},
        }
        current = self.runtime_state.controller_state
        if state not in legal[current]:
            return

        self.runtime_state.controller_state = state
        running = state in {ControllerState.REPLAY_RUNNING, ControllerState.LIVE_RUNNING}
        if running and not self._cycle_timer.isActive():
            self._cycle_timer.start()
        if not running and self._cycle_timer.isActive():
            self._cycle_timer.stop()

        self.window.replay_button.setEnabled(state in {ControllerState.IDLE})
        self.window.live_button.setEnabled(state in {ControllerState.IDLE})
        self.window.home_button.setEnabled(state not in {ControllerState.SAFE})

        if overlay_text is not None:
            self.lane_overlay_requested.emit(overlay_text)
        self._emit_runtime_state()

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
            self._transition_to(ControllerState.FAULTED, overlay_text=error.detail)
            return
        self._step_transport_queue()

        for log_entry in logs:
            self._session_logs.append(log_entry)
            self.log_entry_requested.emit(log_entry)

        self.runtime_state.previous_timestamp_s = frame.timestamp_s
        self.runtime_state.fault_state = self.transport.current_fault_state()

        if self.runtime_state.fault_state == FaultState.SAFE:
            self._protocol_set_mode("SAFE")
            self.runtime_state.operator_mode = OperatorMode.SAFE
            self._transition_to(ControllerState.SAFE, overlay_text="SAFE fault active")
            return
        if self.runtime_state.fault_state == FaultState.WATCHDOG:
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

    def _publish_session_evaluation(self) -> None:
        evaluation = evaluate_logs(tuple(self._session_logs), self._selected_scenarios)
        result_line = "; ".join(
            f"{result.name}:{'PASS' if result.passed else 'FAIL'}" for result in evaluation.scenarios
        )
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

    def recover_safe_to_manual(self) -> bool:
        if self.runtime_state.controller_state != ControllerState.SAFE:
            return False
        if not is_mode_transition_allowed(self.runtime_state.operator_mode.value, "MANUAL"):
            return False
        ack = self._protocol_set_mode("MANUAL")
        if ack is None:
            return False
        self.runtime_state.fault_state = FaultState.NORMAL
        self.runtime_state.operator_mode = OperatorMode.MANUAL
        self._apply_protocol_queue_side_effects(ack.queue_cleared)
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
        if not is_mode_transition_allowed(self.runtime_state.operator_mode.value, "AUTO"):
            return False
        ack = self._protocol_set_mode("AUTO")
        if ack is None:
            return False
        self._apply_protocol_queue_side_effects(ack.queue_cleared)
        self.runtime_state.operator_mode = OperatorMode.AUTO
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
        return self.transport.current_queue_depth()

    def _transport_clear_queue(self) -> None:
        if isinstance(self.transport, MockMcuTransport):
            self.transport.queue.clear()

    def _transport_last_queue_cleared(self) -> bool:
        return self.transport.last_queue_cleared_observation()

    def _apply_protocol_queue_side_effects(self, queue_cleared: bool) -> None:
        if queue_cleared or self._transport_last_queue_cleared():
            self._transport_clear_queue()

    def _protocol_set_mode(self, mode: str):
        response_frame = self._protocol_host.handle_frame(serialize_packet("SET_MODE", (mode,)))
        parsed_response = parse_frame(response_frame)
        ack = parse_ack_tokens((parsed_response.command, *parsed_response.args))
        if ack.status != "ACK":
            return None
        return ack

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
        self._transport_clear_queue()
        self._release_frame_source()
        self.runtime_state.previous_timestamp_s = 0.0
        self.runtime_state.fault_state = FaultState.NORMAL
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
