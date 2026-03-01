from __future__ import annotations

from typing import Protocol

from coloursorter.scheduler import ScheduledCommand

from .types import TransportResponse


class McuTransport(Protocol):
    def send(self, command: ScheduledCommand) -> TransportResponse:
        ...
