from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .serial_interface import AckResponse


@dataclass(frozen=True)
class ActuationRequest:
    """Canonical actuation request independent of wire framing details."""

    command: "ScheduledCommand"
    msg_id: str = "0"


@dataclass(frozen=True)
class ActuationResponse:
    """Canonical MCU response mapped from ACK/NACK metadata tokens."""

    ack: AckResponse
    msg_id: str


@dataclass(frozen=True)
class SensorSnapshot:
    """Minimal sensor/state projection suitable for MCU-friendly contracts."""

    mode: str
    queue_depth: int
    scheduler_state: str
    queue_cleared: bool
    link_state: str | None


class ActuatorInterface(Protocol):
    """Abstract actuator transport contract for firmware translation targets."""

    def encode_actuation(self, request: ActuationRequest) -> bytes:
        ...


class SensorInterface(Protocol):
    """Abstract sensor/state decode contract for firmware translation targets."""

    def decode_response(self, response: ActuationResponse) -> SensorSnapshot:
        ...
