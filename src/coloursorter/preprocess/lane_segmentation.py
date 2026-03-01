from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from coloursorter.model import LaneGeometry


@dataclass(frozen=True)
class LaneSegmentationResult:
    lane: int
    centroid_x_px: float


class LaneGeometryError(ValueError):
    pass


def _extract_scalar(raw_text: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", raw_text, re.MULTILINE)
    if not match:
        raise LaneGeometryError(f"Missing key: {key}")
    return match.group(1).strip()


def _extract_boundaries(raw_text: str) -> tuple[int, ...]:
    match = re.search(r"lane_boundaries_px:\s*(\[[\s\S]*?\])", raw_text)
    if not match:
        raise LaneGeometryError("Missing lane_boundaries_px")
    return tuple(int(x) for x in ast.literal_eval(match.group(1)))


def load_lane_geometry(config_path: str | Path) -> LaneGeometry:
    raw_text = Path(config_path).read_text(encoding="utf-8")
    lane_count = int(_extract_scalar(raw_text, "lane_count"))
    lane_boundaries = _extract_boundaries(raw_text)

    if lane_count != 22:
        raise LaneGeometryError("Expected fixed lane_count=22")
    if len(lane_boundaries) != lane_count + 1:
        raise LaneGeometryError("lane_boundaries_px size must be lane_count + 1")
    if any(b >= lane_boundaries[i + 1] for i, b in enumerate(lane_boundaries[:-1])):
        raise LaneGeometryError("lane_boundaries_px must be strictly increasing")

    return LaneGeometry(
        lane_count=lane_count,
        lane_boundaries_px=lane_boundaries,
        belt_direction_axis=_extract_scalar(raw_text, "belt_direction_axis"),
        mm_per_pixel=float(_extract_scalar(raw_text, "mm_per_pixel")),
        camera_to_reject_mm=float(_extract_scalar(raw_text, "camera_to_reject_mm")),
    )


def lane_for_x_px(x_px: float, geometry: LaneGeometry) -> int | None:
    for lane in range(geometry.lane_count):
        left = geometry.lane_boundaries_px[lane]
        right = geometry.lane_boundaries_px[lane + 1]
        if left <= x_px < right:
            return lane
    return None
