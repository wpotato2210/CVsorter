from __future__ import annotations

from coloursorter.scheduler import ScheduledCommand


def encode_schedule_command(command: ScheduledCommand) -> bytes:
    return (command.to_wire() + "\n").encode("ascii")
