from __future__ import annotations

import math

import pytest

from coloursorter.scheduler import build_scheduled_command, map_segmentation_lane_to_protocol_lane


def test_compute_trigger_mm() -> None:
    command = build_scheduled_command(1, 42.125)
    assert command.lane == 1
    assert command.position_mm == 42.125


def test_reject_non_finite_trigger_mm() -> None:
    with pytest.raises(ValueError):
        build_scheduled_command(0, math.inf)


def test_reject_protocol_lane_out_of_range() -> None:
    with pytest.raises(ValueError):
        build_scheduled_command(8, 1.0)


def test_map_segmentation_lane_to_protocol_lane_is_deterministic() -> None:
    assert map_segmentation_lane_to_protocol_lane(0, 22) == 0
    assert map_segmentation_lane_to_protocol_lane(2, 22) == 0
    assert map_segmentation_lane_to_protocol_lane(3, 22) == 1
    assert map_segmentation_lane_to_protocol_lane(10, 22) == 3
    assert map_segmentation_lane_to_protocol_lane(21, 22) == 7


def test_map_segmentation_lane_to_protocol_lane_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        map_segmentation_lane_to_protocol_lane(22, 22)
