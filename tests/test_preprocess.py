from __future__ import annotations

from pathlib import Path

import pytest

from coloursorter.preprocess import LaneGeometryError, lane_for_x_px, load_lane_geometry


def _lane_config_text(boundaries: list[int]) -> str:
    return (
        "lane_count: 22\n"
        f"lane_boundaries_px: {boundaries}\n"
        "belt_direction_axis: vertical\n"
        "mm_per_pixel: 0.25\n"
        "camera_to_reject_mm: 120.0\n"
    )


def test_load_lane_geometry_parses_and_enforces_structure(tmp_path: Path) -> None:
    config_path = tmp_path / "lane_geometry.yaml"
    boundaries = [i * 10 for i in range(23)]
    config_path.write_text(_lane_config_text(boundaries), encoding="utf-8")

    geometry = load_lane_geometry(config_path)

    assert geometry.lane_count == 22
    assert geometry.lane_boundaries_px[0] == 0
    assert geometry.lane_boundaries_px[-1] == 220
    assert geometry.camera_to_reject_mm == 120.0


def test_load_lane_geometry_rejects_non_increasing_boundaries(tmp_path: Path) -> None:
    config_path = tmp_path / "lane_geometry.yaml"
    boundaries = [i * 10 for i in range(23)]
    boundaries[11] = boundaries[10]
    config_path.write_text(_lane_config_text(boundaries), encoding="utf-8")

    with pytest.raises(LaneGeometryError):
        load_lane_geometry(config_path)


def test_lane_for_x_px_uses_left_closed_right_open_bins(tmp_path: Path) -> None:
    config_path = tmp_path / "lane_geometry.yaml"
    boundaries = [i * 10 for i in range(23)]
    config_path.write_text(_lane_config_text(boundaries), encoding="utf-8")
    geometry = load_lane_geometry(config_path)

    assert lane_for_x_px(0, geometry) == 0
    assert lane_for_x_px(9.999, geometry) == 0
    assert lane_for_x_px(10.0, geometry) == 1
    assert lane_for_x_px(219.999, geometry) == 21
    assert lane_for_x_px(220.0, geometry) is None


def test_load_lane_geometry_rejects_non_positive_lane_count(tmp_path: Path) -> None:
    config_path = tmp_path / "lane_geometry.yaml"
    boundaries = [i * 10 for i in range(23)]
    config_path.write_text(
        _lane_config_text(boundaries).replace("lane_count: 22", "lane_count: 0"),
        encoding="utf-8",
    )

    with pytest.raises(LaneGeometryError):
        load_lane_geometry(config_path)


def test_load_lane_geometry_rejects_invalid_axis(tmp_path: Path) -> None:
    config_path = tmp_path / "lane_geometry.yaml"
    boundaries = [i * 10 for i in range(23)]
    config_path.write_text(
        _lane_config_text(boundaries).replace("belt_direction_axis: vertical", "belt_direction_axis: diagonal"),
        encoding="utf-8",
    )

    with pytest.raises(LaneGeometryError):
        load_lane_geometry(config_path)


def test_lane_for_x_px_rejects_non_finite_coordinate(tmp_path: Path) -> None:
    config_path = tmp_path / "lane_geometry.yaml"
    boundaries = [i * 10 for i in range(23)]
    config_path.write_text(_lane_config_text(boundaries), encoding="utf-8")
    geometry = load_lane_geometry(config_path)

    with pytest.raises(LaneGeometryError):
        lane_for_x_px(float("nan"), geometry)
