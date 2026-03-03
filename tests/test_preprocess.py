from __future__ import annotations

from pathlib import Path

import pytest

from coloursorter.model import FrameMetadata
from coloursorter.preprocess import lane_for_x_px, lane_geometry_for_frame, load_lane_geometry

FIXTURES = Path(__file__).parent / "fixtures"


def test_lane_extraction_matches_22_lane_boundaries() -> None:
    geometry = load_lane_geometry(FIXTURES / "lane_geometry_22.yaml")

    assert geometry.lane_count == 22
    assert lane_for_x_px(0.0, geometry) == 0
    assert lane_for_x_px(47.999, geometry) == 0
    assert lane_for_x_px(48.0, geometry) == 1
    assert lane_for_x_px(1007.999, geometry) == 20
    assert lane_for_x_px(1008.0, geometry) == 21
    assert lane_for_x_px(1055.999, geometry) == 21
    assert lane_for_x_px(-0.001, geometry) is None
    assert lane_for_x_px(1056.0, geometry) is None


def test_lane_extraction_is_deterministic_for_same_input() -> None:
    geometry = load_lane_geometry(FIXTURES / "lane_geometry_22.yaml")

    observed = [lane_for_x_px(432.0, geometry) for _ in range(8)]
    assert observed == [9] * 8


def test_lane_geometry_fixture_rejects_non_monotonic_boundaries(tmp_path: Path) -> None:
    broken = tmp_path / "broken_geometry.yaml"
    broken.write_text(
        "\n".join(
            [
                "lane_count: 22",
                "lane_boundaries_px: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 200, 220]",
                "belt_direction_axis: vertical",
                "mm_per_pixel: 0.1",
                "camera_to_reject_mm: 100",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        load_lane_geometry(broken)


def test_lane_geometry_for_frame_scales_boundaries_with_frame_width() -> None:
    geometry = load_lane_geometry(FIXTURES / "lane_geometry_22.yaml")
    frame = FrameMetadata(frame_id=1, timestamp_s=0.0, image_height_px=720, image_width_px=1100)

    result = lane_geometry_for_frame(frame, geometry)

    assert result.alignment_state == "degraded"
    assert result.alignment_reason == "lane_alignment_misaligned"
    assert lane_for_x_px(100.0, result.lane_geometry) == 2


def test_lane_geometry_for_frame_remains_ok_when_frame_matches_geometry() -> None:
    geometry = load_lane_geometry(FIXTURES / "lane_geometry_22.yaml")
    frame = FrameMetadata(frame_id=2, timestamp_s=0.0, image_height_px=720, image_width_px=1056)

    result = lane_geometry_for_frame(frame, geometry)

    assert result.alignment_state == "ok"
    assert result.alignment_reason is None
