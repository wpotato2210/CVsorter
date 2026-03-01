from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduledCommand:
    lane: int
    position_mm: float

    def to_wire(self) -> str:
        return f"SCHED:{self.lane}:{self.position_mm:.3f}"


def build_scheduled_command(lane: int, position_mm: float) -> ScheduledCommand:
    if lane < 0:
        raise ValueError("lane must be >= 0")
    return ScheduledCommand(lane=lane, position_mm=position_mm)
