from __future__ import annotations

import ast
import math
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
    try:
        parsed = ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError) as exc:
        raise LaneGeometryError("lane_boundaries_px must be a valid integer list") from exc
    if not isinstance(parsed, list):
        raise LaneGeometryError("lane_boundaries_px must be a list")

    boundaries: list[int] = []
    for value in parsed:
        if not isinstance(value, int):
            raise LaneGeometryError("lane_boundaries_px entries must be integers")
        boundaries.append(value)
    return tuple(boundaries)


def _parse_positive_float(raw_text: str, key: str) -> float:
    try:
        value = float(_extract_scalar(raw_text, key))
    except ValueError as exc:
        raise LaneGeometryError(f"{key} must be a valid number") from exc
    if not math.isfinite(value):
        raise LaneGeometryError(f"{key} must be finite")
    if value <= 0:
        raise LaneGeometryError(f"{key} must be > 0")
    return value


def load_lane_geometry(config_path: str | Path) -> LaneGeometry:
    raw_text = Path(config_path).read_text(encoding="utf-8")
    try:
        lane_count = int(_extract_scalar(raw_text, "lane_count"))
    except ValueError as exc:
        raise LaneGeometryError("lane_count must be an integer") from exc
    lane_boundaries = _extract_boundaries(raw_text)

    if lane_count <= 0:
        raise LaneGeometryError("lane_count must be > 0")
    if len(lane_boundaries) != lane_count + 1:
        raise LaneGeometryError("lane_boundaries_px size must be lane_count + 1")
    if any(b >= lane_boundaries[i + 1] for i, b in enumerate(lane_boundaries[:-1])):
        raise LaneGeometryError("lane_boundaries_px must be strictly increasing")

    belt_direction_axis = _extract_scalar(raw_text, "belt_direction_axis")
    if belt_direction_axis not in ("vertical", "horizontal"):
        raise LaneGeometryError("belt_direction_axis must be 'vertical' or 'horizontal'")

    return LaneGeometry(
        lane_count=lane_count,
        lane_boundaries_px=lane_boundaries,
        belt_direction_axis=belt_direction_axis,
        mm_per_pixel=_parse_positive_float(raw_text, "mm_per_pixel"),
        camera_to_reject_mm=_parse_positive_float(raw_text, "camera_to_reject_mm"),
    )


def lane_for_x_px(x_px: float, geometry: LaneGeometry) -> int | None:
    if not math.isfinite(x_px):
        raise LaneGeometryError("x_px must be finite")
    for lane in range(geometry.lane_count):
        left = geometry.lane_boundaries_px[lane]
        right = geometry.lane_boundaries_px[lane + 1]
        if left <= x_px < right:
            return lane
    return None
