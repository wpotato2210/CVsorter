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


def _write_calibration(path: Path, mm_per_pixel: float) -> None:
    path.write_text(
        json.dumps(
            {
                "mm_per_pixel": mm_per_pixel,
                "calibration_hash": expected_calibration_hash(mm_per_pixel),
            }
        ),
        encoding="utf-8",
    )


def test_camera_ingest_preserves_frame_id_and_geometry_projection(tmp_path: Path) -> None:
    lane_path = tmp_path / "lane_geometry.yaml"
    calibration_path = tmp_path / "calibration.json"
    _write_lane_config(lane_path)
    _write_calibration(calibration_path, mm_per_pixel=0.5)

    runner = PipelineRunner(lane_path, calibration_path)
    frame = FrameMetadata(frame_id=17, timestamp_s=12.5, image_height_px=1080, image_width_px=1920)
    detection = ObjectDetection(
        object_id="cam-obj-001",
        centroid_x_px=35.0,
        centroid_y_px=200.0,
        classification="accept",
    )

    result = runner.run(frame, [detection])

    assert len(result.decisions) == 1
    decision = result.decisions[0]
    assert decision.frame_id == 17
    assert decision.object_id == "cam-obj-001"
    assert decision.lane == 3
    assert decision.centroid_mm.x_mm == 17.5
    assert decision.centroid_mm.y_mm == 100.0
    assert decision.trigger_mm == 200.0
    assert result.schedule_commands == ()
