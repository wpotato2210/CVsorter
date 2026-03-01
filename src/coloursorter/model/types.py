from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class FrameMetadata:
    frame_id: int
    timestamp_s: float
    image_height_px: int
    image_width_px: int


@dataclass(frozen=True)
class LaneGeometry:
    lane_count: int
    lane_boundaries_px: tuple[int, ...]
    belt_direction_axis: Literal["vertical", "horizontal"]
    mm_per_pixel: float
    camera_to_reject_mm: float


@dataclass(frozen=True)
class CentroidMM:
    x_mm: float
    y_mm: float


@dataclass(frozen=True)
class TriggerMM:
    lane: int
    position_mm: float


@dataclass(frozen=True)
class DecisionPayload:
    frame_id: int
    object_id: str
    lane: int
    centroid_mm: CentroidMM
    trigger_mm: float
    classification: str
    rejection_reason: str | None


@dataclass(frozen=True)
class ObjectDetection:
    object_id: str
    centroid_x_px: float
    centroid_y_px: float
    classification: str
