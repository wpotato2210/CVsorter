from __future__ import annotations

from typing import TYPE_CHECKING

from .abstractions import ActuationRequest
from .adapters import WireActuatorAdapter

if TYPE_CHECKING:
    from coloursorter.scheduler import ScheduledCommand


_WIRE_ACTUATOR = WireActuatorAdapter()


def encode_schedule_command(command: ScheduledCommand) -> bytes:
    return _WIRE_ACTUATOR.encode_actuation(ActuationRequest(command=command))
