from __future__ import annotations

from dataclasses import dataclass

from coloursorter.protocol.constants import LANE_MAX, LANE_MIN, TRIGGER_MM_MAX, TRIGGER_MM_MIN

MIN_TRIGGER_MM = TRIGGER_MM_MIN
MAX_TRIGGER_MM = TRIGGER_MM_MAX


@dataclass(frozen=True)
class ScheduledCommand:
    lane: int
    position_mm: float



def build_scheduled_command(lane: int, position_mm: float) -> ScheduledCommand:
    if lane < LANE_MIN or lane > LANE_MAX:
        raise ValueError(f"lane must be in range {LANE_MIN}..{LANE_MAX}")
    if position_mm < MIN_TRIGGER_MM or position_mm > MAX_TRIGGER_MM:
        raise ValueError(f"position_mm must be in range {MIN_TRIGGER_MM}..{MAX_TRIGGER_MM}")
    return ScheduledCommand(lane=lane, position_mm=position_mm)
