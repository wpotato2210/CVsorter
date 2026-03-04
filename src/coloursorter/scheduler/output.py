from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


PROTOCOL_LANE_MIN = 0
PROTOCOL_LANE_MAX = 7
PROTOCOL_LANE_COUNT = (PROTOCOL_LANE_MAX - PROTOCOL_LANE_MIN) + 1


@dataclass(frozen=True)
class ScheduledCommand:
    lane: int
    position_mm: float

    def to_wire(self) -> str:
        return f"SCHED:{self.lane}:{self.position_mm:.3f}"


def build_scheduled_command(lane: int, position_mm: float) -> ScheduledCommand:
    if lane < PROTOCOL_LANE_MIN or lane > PROTOCOL_LANE_MAX:
        raise ValueError(f"lane must be within protocol range [{PROTOCOL_LANE_MIN}, {PROTOCOL_LANE_MAX}]")
    if not isfinite(position_mm):
        raise ValueError("position_mm must be finite")
    return ScheduledCommand(lane=lane, position_mm=position_mm)


def map_segmentation_lane_to_protocol_lane(segmentation_lane: int, segmentation_lane_count: int) -> int:
    if segmentation_lane_count <= 0:
        raise ValueError("segmentation_lane_count must be > 0")
    if segmentation_lane < 0 or segmentation_lane >= segmentation_lane_count:
        raise ValueError("segmentation_lane must be within segmentation lane range")

    protocol_lane = (segmentation_lane * PROTOCOL_LANE_COUNT) // segmentation_lane_count
    if protocol_lane < PROTOCOL_LANE_MIN or protocol_lane > PROTOCOL_LANE_MAX:
        raise ValueError("mapped protocol lane is out of protocol range")
    return protocol_lane
