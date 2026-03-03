from __future__ import annotations

from dataclasses import dataclass

from coloursorter.protocol.constants import CMD_SCHED

from .abstractions import (
    ActuationRequest,
    ActuationResponse,
    ActuatorInterface,
    SensorInterface,
    SensorSnapshot,
)
from .serial_interface import encode_packet_bytes


@dataclass(frozen=True)
class WireActuatorAdapter(ActuatorInterface):
    """Adapter from ActuationRequest to protocol wire frame bytes."""

    def encode_actuation(self, request: ActuationRequest) -> bytes:
        command = request.command
        return encode_packet_bytes(
            CMD_SCHED,
            (command.lane, f"{command.position_mm:.3f}"),
            msg_id=request.msg_id,
        )


@dataclass(frozen=True)
class AckSensorAdapter(SensorInterface):
    """Adapter from ACK/NACK response projection to sensor snapshot."""

    def decode_response(self, response: ActuationResponse) -> SensorSnapshot:
        ack = response.ack
        return SensorSnapshot(
            mode=ack.mode or "AUTO",
            queue_depth=ack.queue_depth or 0,
            scheduler_state=ack.scheduler_state or "IDLE",
            queue_cleared=ack.queue_cleared,
            link_state=ack.link_state,
        )
