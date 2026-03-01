from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduledCommand:
    lane: int
    position_mm: float



def build_scheduled_command(lane: int, position_mm: float) -> ScheduledCommand:
    if lane < 0 or lane > 21:
        raise ValueError("lane must be in range 0..21")
    return ScheduledCommand(lane=lane, position_mm=position_mm)
