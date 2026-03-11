from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

from coloursorter.deploy.pipeline import PipelineResult, PipelineRunner
from coloursorter.model import FrameMetadata, ObjectDetection

FIXTURES = Path(__file__).parent / "fixtures"


def _build_runner() -> PipelineRunner:
    return PipelineRunner(FIXTURES / "lane_geometry_22.yaml", FIXTURES / "calibration_edge_valid.json")


def _build_inputs() -> tuple[FrameMetadata, list[ObjectDetection]]:
    frame = FrameMetadata(frame_id=44, timestamp_s=44.0, image_height_px=240, image_width_px=320)
    detections = [
        ObjectDetection(
            "obj-contract-1",
            centroid_x_px=40.0,
            centroid_y_px=60.0,
            classification="reject",
            infection_score=1.0,
        )
    ]
    return frame, detections


def test_pipeline_concurrent_run_is_deterministic_for_static_configs() -> None:
    """Concurrency contract: shared runner supports deterministic concurrent run() with immutable configs."""
    runner = _build_runner()
    frame, detections = _build_inputs()

    expected = runner.run(frame=frame, detections=detections)

    start_barrier = threading.Barrier(9)

    def _invoke_once() -> PipelineResult:
        start_barrier.wait(timeout=5)
        return runner.run(frame=frame, detections=detections)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_invoke_once) for _ in range(8)]
        start_barrier.wait(timeout=5)

    results = [future.result(timeout=5) for future in futures]

    assert results
    assert all(result == expected for result in results)
