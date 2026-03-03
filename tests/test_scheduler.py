from __future__ import annotations

from pathlib import Path
import json
import os

import pytest
import time

from coloursorter.calibration import load_calibration
from coloursorter.deploy import PipelineRunner
from coloursorter.model import FrameMetadata, ObjectDetection
from coloursorter.scheduler import build_scheduled_command

FIXTURES = Path(__file__).parent / "fixtures"


def test_pixel_to_mm_mapping_is_deterministic() -> None:
    calibration = load_calibration(FIXTURES / "calibration_edge_valid.json")

    measurements = [calibration.px_to_mm(512.5) for _ in range(6)]
    assert measurements == [measurements[0]] * 6
    assert measurements[0] == pytest.approx(63.27160436865)


def test_scheduler_trigger_mm_adds_camera_offset_and_centroid_mm() -> None:
    runner = PipelineRunner(
        lane_config_path=FIXTURES / "lane_geometry_22.yaml",
        calibration_path=FIXTURES / "calibration_edge_valid.json",
    )

    frame = FrameMetadata(frame_id=7, timestamp_s=1.25, image_height_px=720, image_width_px=1056)
    detection = ObjectDetection(
        object_id="obj-1",
        centroid_x_px=120.0,
        centroid_y_px=240.0,
        classification="reject",
    )

    result = runner.run(frame=frame, detections=[detection])
    assert len(result.decisions) == 1
    assert len(result.schedule_commands) == 1

    decision = result.decisions[0]
    assert decision.lane == 2
    assert decision.rejection_reason == "classified_reject"
    assert decision.trigger_mm == 304.62962936288

    sched = result.schedule_commands[0]
    assert sched.lane == 2
    assert sched.position_mm == decision.trigger_mm


def test_scheduler_enforces_full_22_lane_range_boundaries() -> None:
    assert build_scheduled_command(0, 10.0).lane == 0
    assert build_scheduled_command(21, 10.0).lane == 21

    with pytest.raises(ValueError, match="range 0..21"):
        build_scheduled_command(-1, 10.0)

    with pytest.raises(ValueError, match="range 0..21"):
        build_scheduled_command(22, 10.0)


def test_scheduler_enforces_trigger_mm_bounds() -> None:
    assert build_scheduled_command(1, 0.0).position_mm == 0.0
    assert build_scheduled_command(1, 2000.0).position_mm == 2000.0

    with pytest.raises(ValueError, match="0.0..2000.0"):
        build_scheduled_command(1, -0.001)

    with pytest.raises(ValueError, match="0.0..2000.0"):
        build_scheduled_command(1, 2000.001)


def test_pipeline_runner_reload_calibration_on_change(tmp_path: Path) -> None:
    lane_path = FIXTURES / "lane_geometry_22.yaml"
    calibration_path = tmp_path / "calibration.json"
    valid = json.loads((FIXTURES / "calibration_edge_valid.json").read_text(encoding="utf-8"))
    calibration_path.write_text(json.dumps(valid), encoding="utf-8")
    runner = PipelineRunner(lane_config_path=lane_path, calibration_path=calibration_path)

    detection = ObjectDetection(
        object_id="det-1",
        centroid_x_px=100.0,
        centroid_y_px=100.0,
        classification="reject",
        infection_score=0.9,
    )
    frame = FrameMetadata(frame_id=1, timestamp_s=0.1, image_height_px=720, image_width_px=1056)
    first = runner.run(frame, [detection]).decisions[0]

    bad = dict(valid)
    bad["calibration_hash"] = "invalid"
    time.sleep(0.02)
    calibration_path.write_text(json.dumps(bad), encoding="utf-8")
    os.utime(calibration_path, None)
    second = runner.run(frame, [detection]).decisions[0]

    assert first.rejection_reason != "Invalid calibration hash: expected deterministic SHA-256 of mm_per_pixel"
    assert second.rejection_reason == "Invalid calibration hash: expected deterministic SHA-256 of mm_per_pixel"
