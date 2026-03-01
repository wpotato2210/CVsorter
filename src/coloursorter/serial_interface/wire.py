from __future__ import annotations

from coloursorter.scheduler import ScheduledCommand
from coloursorter.serial_interface.serial_interface import encode_packet_bytes


def encode_schedule_command(command: ScheduledCommand) -> bytes:
    return encode_packet_bytes("SCHED", (command.lane, f"{command.position_mm:.3f}"))
