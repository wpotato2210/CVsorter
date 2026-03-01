from __future__ import annotations

from typing import TYPE_CHECKING

from coloursorter.protocol.constants import CMD_SCHED
from coloursorter.serial_interface.serial_interface import encode_packet_bytes

if TYPE_CHECKING:
    from coloursorter.scheduler import ScheduledCommand


def encode_schedule_command(command: ScheduledCommand) -> bytes:
    return encode_packet_bytes(CMD_SCHED, (command.lane, f"{command.position_mm:.3f}"))
