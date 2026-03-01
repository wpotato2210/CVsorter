from __future__ import annotations

from dataclasses import dataclass


MIN_TRIGGER_MM = 0.0
MAX_TRIGGER_MM = 2000.0


@dataclass(frozen=True)
class ScheduledCommand:
    lane: int
    position_mm: float



def build_scheduled_command(lane: int, position_mm: float) -> ScheduledCommand:
    if lane < 0 or lane > 21:
        raise ValueError("lane must be in range 0..21")
    if position_mm < MIN_TRIGGER_MM or position_mm > MAX_TRIGGER_MM:
        raise ValueError("position_mm must be in range 0.0..2000.0")
    return ScheduledCommand(lane=lane, position_mm=position_mm)
