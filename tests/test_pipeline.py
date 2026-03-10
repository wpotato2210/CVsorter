from __future__ import annotations

from pathlib import Path

from coloursorter.deploy.pipeline import PipelineRunner
from coloursorter.model import FrameMetadata, ObjectDetection

FIXTURES = Path(__file__).parent / "fixtures"


def test_pipeline_returns_decision_payload_for_in_lane_detection() -> None:
    """Normal path: in-lane detection returns deterministic decision payload."""
    runner = PipelineRunner(FIXTURES / "lane_geometry_22.yaml", FIXTURES / "calibration_edge_valid.json")
    frame = FrameMetadata(frame_id=1, timestamp_s=1.0, image_height_px=240, image_width_px=320)
    detection = ObjectDetection("obj-1", centroid_x_px=40.0, centroid_y_px=60.0, classification="reject", infection_score=1.0)
    result = runner.run(frame=frame, detections=[detection])
    assert len(result.decisions) == 1
    assert result.decisions[0].lane >= 0
    assert result.decisions[0].object_id == "obj-1"


def test_pipeline_returns_fault_reason_when_detection_out_of_lane() -> None:
    """Boundary path: x outside lane boundaries yields lane=-1 and no schedule."""
    runner = PipelineRunner(FIXTURES / "lane_geometry_22.yaml", FIXTURES / "calibration_edge_valid.json")
    frame = FrameMetadata(frame_id=2, timestamp_s=2.0, image_height_px=240, image_width_px=320)
    detection = ObjectDetection("obj-2", centroid_x_px=10000.0, centroid_y_px=10.0, classification="reject", infection_score=1.0)
    result = runner.run(frame=frame, detections=[detection])
    assert result.decisions[0].lane == -1
    assert result.scheduled_events == ()
