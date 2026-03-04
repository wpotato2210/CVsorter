from __future__ import annotations

import json
from pathlib import Path

from coloursorter.calibration.mapping import expected_calibration_hash
from coloursorter.deploy import PipelineRunner
from coloursorter.model import FrameMetadata, ObjectDetection


def _write_lane_config(path: Path) -> None:
    path.write_text(
        "lane_count: 22\n"
        f"lane_boundaries_px: {[i * 10 for i in range(23)]}\n"
        "belt_direction_axis: vertical\n"
        "mm_per_pixel: 0.5\n"
        "camera_to_reject_mm: 100.0\n",
        encoding="utf-8",
    )


def _write_calibration(path: Path, mm_per_pixel: float, *, invalid_hash: bool = False) -> None:
    calibration_hash = expected_calibration_hash(mm_per_pixel)
    if invalid_hash:
        calibration_hash = "0" * 64

    path.write_text(
        json.dumps({"mm_per_pixel": mm_per_pixel, "calibration_hash": calibration_hash}),
        encoding="utf-8",
    )


def _frame() -> FrameMetadata:
    return FrameMetadata(frame_id=1, timestamp_s=1.0, image_height_px=480, image_width_px=640)


def test_pipeline_marks_invalid_calibration_and_emits_no_commands(tmp_path: Path) -> None:
    lane_path = tmp_path / "lane_geometry.yaml"
    calibration_path = tmp_path / "calibration.json"
    _write_lane_config(lane_path)
    _write_calibration(calibration_path, mm_per_pixel=0.5, invalid_hash=True)

    result = PipelineRunner(lane_path, calibration_path).run(
        _frame(), [ObjectDetection("reject-invalid-cal", 15.0, 20.0, "reject")]
    )

    assert result.decisions[0].rejection_reason == (
        "Invalid calibration hash: expected deterministic SHA-256 of mm_per_pixel"
    )
    assert result.schedule_commands == ()


def test_pipeline_marks_out_of_lane_detection_and_emits_no_command(tmp_path: Path) -> None:
    lane_path = tmp_path / "lane_geometry.yaml"
    calibration_path = tmp_path / "calibration.json"
    _write_lane_config(lane_path)
    _write_calibration(calibration_path, mm_per_pixel=0.5)

    result = PipelineRunner(lane_path, calibration_path).run(
        _frame(), [ObjectDetection("reject-outside", 500.0, 20.0, "reject")]
    )

    assert result.decisions[0].lane == -1
    assert result.decisions[0].rejection_reason == "out_of_lane_bounds"
    assert result.schedule_commands == ()


def test_pipeline_emits_commands_only_for_in_lane_rejects(tmp_path: Path) -> None:
    lane_path = tmp_path / "lane_geometry.yaml"
    calibration_path = tmp_path / "calibration.json"
    _write_lane_config(lane_path)
    _write_calibration(calibration_path, mm_per_pixel=0.5)

    detections = [
        ObjectDetection("reject-in-lane", 15.0, 20.0, "reject"),
        ObjectDetection("accept-in-lane", 25.0, 20.0, "accept"),
        ObjectDetection("reject-outside", 500.0, 20.0, "reject"),
    ]
    result = PipelineRunner(lane_path, calibration_path).run(_frame(), detections)

    reasons = {decision.object_id: decision.rejection_reason for decision in result.decisions}
    assert reasons == {
        "reject-in-lane": "classified_reject",
        "accept-in-lane": None,
        "reject-outside": "out_of_lane_bounds",
    }
    assert len(result.schedule_commands) == 1
    assert result.schedule_commands[0].lane == 0
    assert result.schedule_commands[0].position_mm == 110.0
