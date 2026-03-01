from __future__ import annotations

from typing import Protocol

from coloursorter.scheduler import ScheduledCommand

from .types import FaultState, TransportResponse


class McuTransport(Protocol):
    def send(self, command: ScheduledCommand) -> TransportResponse:
        ...

    def current_fault_state(self) -> FaultState:
        ...

    def current_queue_depth(self) -> int:
        ...

    def last_queue_cleared_observation(self) -> bool:
        ...
