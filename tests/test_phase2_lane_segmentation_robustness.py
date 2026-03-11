from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "coloursorter" / "preprocess" / "lane_segmentation.py"
SPEC = importlib.util.spec_from_file_location("phase2_lane_segmentation", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module spec from {MODULE_PATH}")
LANE_SEGMENTATION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LANE_SEGMENTATION
SPEC.loader.exec_module(LANE_SEGMENTATION)
LaneGeometryError = LANE_SEGMENTATION.LaneGeometryError
lane_for_x_px = LANE_SEGMENTATION.lane_for_x_px
load_lane_geometry = LANE_SEGMENTATION.load_lane_geometry


def test_phase2_lane_segmentation_robustness_x_boundaries_are_deterministic_across_repeated_queries() -> None:
    geometry = load_lane_geometry(FIXTURES / "lane_geometry_22.yaml")

    sample_points = (0.0, 47.5, 48.0, 95.0, 1008.0, 1055.999, -1.0, 2000.0)
    first_pass = tuple(lane_for_x_px(x_px, geometry) for x_px in sample_points)
    second_pass = tuple(lane_for_x_px(x_px, geometry) for x_px in sample_points)

    assert first_pass == second_pass


def test_phase2_lane_segmentation_robustness_y_rejects_non_fixed_lane_count(tmp_path: Path) -> None:
    bad_config = "\n".join(
        (
            "lane_count: 21",
            "lane_boundaries_px: [0, 1, 2, 3]",
            "belt_direction_axis: vertical",
            "mm_per_pixel: 0.1",
            "camera_to_reject_mm: 100",
        )
    )
    config_path = tmp_path / "lane_geometry_bad_count.yaml"
    config_path.write_text(bad_config, encoding="utf-8")

    with pytest.raises(LaneGeometryError, match="fixed lane_count=22"):
        load_lane_geometry(config_path)


def test_phase2_lane_segmentation_robustness_z_rejects_non_monotonic_boundaries(tmp_path: Path) -> None:
    bad_config = "\n".join(
        (
            "lane_count: 22",
            "lane_boundaries_px: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 200, 220]",
            "belt_direction_axis: vertical",
            "mm_per_pixel: 0.1",
            "camera_to_reject_mm: 0.1",
        )
    )
    config_path = tmp_path / "lane_geometry_bad_boundaries.yaml"
    config_path.write_text(bad_config, encoding="utf-8")

    with pytest.raises(LaneGeometryError, match="strictly increasing"):
        load_lane_geometry(config_path)
