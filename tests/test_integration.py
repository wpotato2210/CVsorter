from __future__ import annotations

import json
from pathlib import Path

from coloursorter.calibration.mapping import expected_calibration_hash
from coloursorter.deploy import PipelineRunner
from coloursorter.model import FrameMetadata, ObjectDetection


def _write_lane_config(path: Path) -> None:
    boundaries = [i * 10 for i in range(23)]
    path.write_text(
        "lane_count: 22\n"
        f"lane_boundaries_px: {boundaries}\n"
        "belt_direction_axis: vertical\n"
        "mm_per_pixel: 0.5\n"
        "camera_to_reject_mm: 100.0\n",
        encoding="utf-8",
    )


def _write_calibration(path: Path, mm_per_pixel: float, tampered: bool = False) -> None:
    calibration_hash = expected_calibration_hash(mm_per_pixel)
    if tampered:
        calibration_hash = "0" * 64
    path.write_text(
        json.dumps({"mm_per_pixel": mm_per_pixel, "calibration_hash": calibration_hash}),
        encoding="utf-8",
    )


def test_pipeline_assigns_reasons_and_schedules_rejects_only(tmp_path: Path) -> None:
    lane_path = tmp_path / "lane_geometry.yaml"
    calibration_path = tmp_path / "calibration.json"
    _write_lane_config(lane_path)
    _write_calibration(calibration_path, mm_per_pixel=0.5)

    runner = PipelineRunner(lane_path, calibration_path)
    frame = FrameMetadata(frame_id=101, timestamp_s=1.0, image_height_px=480, image_width_px=640)
    detections = [
        ObjectDetection("reject-in-lane", 15.0, 20.0, "reject"),
        ObjectDetection("accept-in-lane", 25.0, 20.0, "accept"),
        ObjectDetection("reject-out-of-bounds", 500.0, 10.0, "reject"),
    ]

    result = runner.run(frame, detections)

    decisions_by_id = {d.object_id: d for d in result.decisions}
    assert decisions_by_id["reject-in-lane"].rejection_reason == "classified_reject"
    assert decisions_by_id["accept-in-lane"].rejection_reason is None
    assert decisions_by_id["reject-out-of-bounds"].lane == -1
    assert decisions_by_id["reject-out-of-bounds"].rejection_reason == "out_of_lane_bounds"

    assert len(result.schedule_commands) == 1
    command = result.schedule_commands[0]
    assert command.lane == 1
    assert command.position_mm == 110.0


def test_pipeline_skips_scheduling_when_calibration_is_invalid(tmp_path: Path) -> None:
    lane_path = tmp_path / "lane_geometry.yaml"
    calibration_path = tmp_path / "calibration.json"
    _write_lane_config(lane_path)
    _write_calibration(calibration_path, mm_per_pixel=0.5, tampered=True)

    runner = PipelineRunner(lane_path, calibration_path)
    frame = FrameMetadata(frame_id=102, timestamp_s=2.0, image_height_px=480, image_width_px=640)
    detections = [ObjectDetection("reject-needs-calibration", 15.0, 20.0, "reject")]

    result = runner.run(frame, detections)

    assert len(result.decisions) == 1
    assert result.decisions[0].rejection_reason == (
        "Invalid calibration hash: expected deterministic SHA-256 of mm_per_pixel"
    )
    assert result.schedule_commands == ()
