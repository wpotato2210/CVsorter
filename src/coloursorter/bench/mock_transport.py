from __future__ import annotations

from dataclasses import dataclass, field

from coloursorter.protocol import OpenSpecV3Host
from coloursorter.scheduler import ScheduledCommand
from coloursorter.serial_interface import AckResponse, parse_ack_tokens, parse_frame, serialize_packet

from .types import AckCode, FaultState, TransportResponse


@dataclass
class MockTransportConfig:
    max_queue_depth: int
    base_round_trip_ms: float
    per_item_penalty_ms: float


@dataclass
class MockMcuTransport:
    config: MockTransportConfig
    fault_state: FaultState = FaultState.NORMAL
    queue: list[ScheduledCommand] = field(default_factory=list)
    _last_queue_cleared: bool = False
    _host: OpenSpecV3Host = field(init=False)

    def __post_init__(self) -> None:
        self._host = OpenSpecV3Host(max_queue_depth=self.config.max_queue_depth)

    def send(self, command: ScheduledCommand) -> TransportResponse:
        self._last_queue_cleared = False
        if self.fault_state == FaultState.SAFE:
            return TransportResponse(AckCode.NACK_SAFE, len(self.queue), self._round_trip_ms(), FaultState.SAFE, nack_code=5, nack_detail="SAFE")
        if self.fault_state == FaultState.WATCHDOG:
            return TransportResponse(AckCode.NACK_WATCHDOG, len(self.queue), self._round_trip_ms(), FaultState.WATCHDOG, nack_code=None, nack_detail="WATCHDOG")

        ack = self.send_command("SCHED", (command.lane, f"{command.position_mm:.3f}"))
        if ack.status == "ACK":
            ack_code = AckCode.ACK
            fault_state = FaultState.NORMAL
        elif ack.nack_code == 6:
            ack_code = AckCode.NACK_QUEUE_FULL
            fault_state = FaultState.NORMAL
        elif ack.nack_code == 7:
            ack_code = AckCode.NACK_BUSY
            fault_state = FaultState.NORMAL
        elif ack.nack_code == 5:
            ack_code = AckCode.NACK_SAFE
            fault_state = FaultState.SAFE
        else:
            ack_code = AckCode.NACK_SAFE
            fault_state = FaultState.SAFE
        self.queue = [ScheduledCommand(lane=lane, position_mm=trigger_mm) for lane, trigger_mm in self._host.queue]
        return TransportResponse(
            ack_code=ack_code,
            queue_depth=ack.queue_depth or 0,
            round_trip_ms=self._round_trip_ms(),
            fault_state=fault_state,
            scheduler_state=ack.scheduler_state or "IDLE",
            mode=ack.mode or "AUTO",
            queue_cleared=ack.queue_cleared,
            nack_code=ack.nack_code,
            nack_detail=ack.detail,
        )

    def send_command(self, command: str, args: tuple[object, ...] = ()) -> AckResponse:
        frame = serialize_packet(command, args)
        response_frame = self._host.handle_frame(frame)
        parsed = parse_frame(response_frame)
        ack = parse_ack_tokens((parsed.command, *parsed.args))
        self._last_queue_cleared = ack.queue_cleared
        self.queue = [ScheduledCommand(lane=lane, position_mm=trigger_mm) for lane, trigger_mm in self._host.queue]
        if ack.mode == "SAFE":
            self.fault_state = FaultState.SAFE
        elif self.fault_state != FaultState.WATCHDOG:
            self.fault_state = FaultState.NORMAL
        return ack

    def step_queue(self, items_to_consume: int = 1) -> None:
        consume = max(0, min(items_to_consume, len(self._host.queue)))
        self._last_queue_cleared = False
        if consume:
            del self._host.queue[:consume]
            self._host.scheduler_state = "IDLE" if not self._host.queue else "ACTIVE"
            self._last_queue_cleared = len(self._host.queue) == 0
        self.queue = [ScheduledCommand(lane=lane, position_mm=trigger_mm) for lane, trigger_mm in self._host.queue]


    def clear_queue_state(self) -> None:
        self._host.queue.clear()
        self._host.scheduler_state = "IDLE"
        self.queue.clear()
        self._last_queue_cleared = True

    def current_fault_state(self) -> FaultState:
        return self.fault_state

    def current_queue_depth(self) -> int:
        return len(self.queue)

    def last_queue_cleared_observation(self) -> bool:
        return self._last_queue_cleared

    def _round_trip_ms(self) -> float:
        return self.config.base_round_trip_ms + len(self.queue) * self.config.per_item_penalty_ms
