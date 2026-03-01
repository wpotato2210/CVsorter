from __future__ import annotations

from dataclasses import dataclass, field

from coloursorter.scheduler import ScheduledCommand

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

    def send(self, command: ScheduledCommand) -> TransportResponse:
        self._last_queue_cleared = False
        if self.fault_state == FaultState.SAFE:
            return TransportResponse(AckCode.NACK_SAFE, len(self.queue), self._round_trip_ms(), FaultState.SAFE, nack_code=5, nack_detail="SAFE")
        if self.fault_state == FaultState.WATCHDOG:
            return TransportResponse(AckCode.NACK_WATCHDOG, len(self.queue), self._round_trip_ms(), FaultState.WATCHDOG, nack_code=None, nack_detail="WATCHDOG")
        if len(self.queue) >= self.config.max_queue_depth:
            return TransportResponse(AckCode.NACK_QUEUE_FULL, len(self.queue), self._round_trip_ms(), FaultState.NORMAL, nack_code=6, nack_detail="QUEUE_FULL")

        self.queue.append(command)
        return TransportResponse(AckCode.ACK, len(self.queue), self._round_trip_ms(), FaultState.NORMAL)

    def step_queue(self, items_to_consume: int = 1) -> None:
        consume = max(0, min(items_to_consume, len(self.queue)))
        self._last_queue_cleared = False
        if consume:
            del self.queue[:consume]
            self._last_queue_cleared = len(self.queue) == 0

    def current_fault_state(self) -> FaultState:
        return self.fault_state

    def current_queue_depth(self) -> int:
        return len(self.queue)

    def last_queue_cleared_observation(self) -> bool:
        return self._last_queue_cleared

    def _round_trip_ms(self) -> float:
        return self.config.base_round_trip_ms + len(self.queue) * self.config.per_item_penalty_ms
