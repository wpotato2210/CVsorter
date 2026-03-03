from __future__ import annotations

from dataclasses import dataclass

from coloursorter.model import FrameMetadata, LaneGeometry


@dataclass(frozen=True)
class FrameLaneGeometry:
    lane_geometry: LaneGeometry
    lane_scale_x: float
    lane_offset_x_px: float
    alignment_state: str
    alignment_reason: str | None


class LaneAlignmentError(ValueError):
    pass


def lane_geometry_for_frame(
    frame: FrameMetadata,
    geometry: LaneGeometry,
    *,
    max_scale_deviation_ratio: float = 0.02,
) -> FrameLaneGeometry:
    configured_width_px = geometry.lane_boundaries_px[-1] - geometry.lane_boundaries_px[0]
    if configured_width_px <= 0:
        raise LaneAlignmentError("lane geometry width must be positive")

    observed_width_px = frame.image_width_px
    if observed_width_px <= 0:
        raise LaneAlignmentError("frame image_width_px must be positive")

    lane_scale_x = observed_width_px / configured_width_px
    lane_offset_x_px = -geometry.lane_boundaries_px[0] * lane_scale_x
    adjusted_boundaries = tuple(int(round(boundary * lane_scale_x + lane_offset_x_px)) for boundary in geometry.lane_boundaries_px)
    adjusted_geometry = LaneGeometry(
        lane_count=geometry.lane_count,
        lane_boundaries_px=adjusted_boundaries,
        belt_direction_axis=geometry.belt_direction_axis,
        mm_per_pixel=geometry.mm_per_pixel,
        camera_to_reject_mm=geometry.camera_to_reject_mm,
    )

    scale_deviation_ratio = abs(lane_scale_x - 1.0)
    if scale_deviation_ratio > max_scale_deviation_ratio:
        return FrameLaneGeometry(
            lane_geometry=adjusted_geometry,
            lane_scale_x=lane_scale_x,
            lane_offset_x_px=lane_offset_x_px,
            alignment_state="degraded",
            alignment_reason="lane_alignment_misaligned",
        )

    return FrameLaneGeometry(
        lane_geometry=adjusted_geometry,
        lane_scale_x=lane_scale_x,
        lane_offset_x_px=lane_offset_x_px,
        alignment_state="ok",
        alignment_reason=None,
    )
