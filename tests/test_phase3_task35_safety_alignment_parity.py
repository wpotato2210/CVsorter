from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
import itertools

from coloursorter.bench.runner import BenchRunner, BenchSafetyConfig
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy import CaptureBaselineConfig, PipelineRunner, capture_fault_reason
from coloursorter.eval.reject_profiles import load_reject_profiles, selected_thresholds
from coloursorter.model import FrameMetadata, ObjectDetection


class _DeterministicTransport:
    def __init__(self, *, scheduler_state: str = "IDLE", ack_code: str = "ACK") -> None:
        self.scheduler_state = scheduler_state
        self.ack_code = ack_code

    def send(self, _command: object) -> SimpleNamespace:
        return SimpleNamespace(
            queue_depth=0,
            scheduler_state=self.scheduler_state,
            mode="AUTO",
            queue_cleared=False,
            round_trip_ms=1.0,
            ack_code=self.ack_code,
            nack_code=None,
            nack_detail=None,
        )


def _runtime_thresholds() -> dict[str, float]:
    profiles, selected_name = load_reject_profiles("configs/reject_profiles.yaml")
    resolved = selected_thresholds(profiles, selected_name)
    return {key: float(resolved[key]) for key in sorted(resolved)}


def _build_detection(score: float) -> ObjectDetection:
    return ObjectDetection(
        object_id="obj-35",
        centroid_x_px=80.0,
        centroid_y_px=80.0,
        classification="reject",
        infection_score=score,
    )


def test_phase3_task35_bench_live_fault_vectors_have_identical_safety_decisions() -> None:
    thresholds = _runtime_thresholds()
    frame = FrameMetadata(frame_id=35, timestamp_s=1.0, image_height_px=240, image_width_px=1100)
    detection = _build_detection(1.0)
    baseline = CaptureBaselineConfig()

    vectors = (
        {
            "name": "capture_fault",
            "preprocess_metrics": {"preprocess_valid": False, "luma_after": 120.0},
            "perf_counter": [10.0, 10.001, 10.002, 10.003, 10.004, 10.005],
            "enqueued_monotonic_s": 9.999,
            "captured_monotonic_s": 9.999,
            "expected_scheduler_state": "SKIPPED",
        },
        {
            "name": "queue_age_fault",
            "preprocess_metrics": None,
            "perf_counter": [20.0, 20.001, 20.002, 20.003, 20.004, 20.005],
            "enqueued_monotonic_s": 19.8,
            "captured_monotonic_s": 19.999,
            "expected_scheduler_state": "SAFE",
        },
        {
            "name": "frame_staleness_fault",
            "preprocess_metrics": None,
            "perf_counter": [30.0, 30.001, 30.002, 30.003, 30.004, 30.005],
            "enqueued_monotonic_s": 29.999,
            "captured_monotonic_s": 29.8,
            "expected_scheduler_state": "SAFE",
        },
    )

    for vector in vectors:
        live_result = PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json").run(
            frame=frame,
            detections=[detection],
            thresholds=thresholds,
            capture_fault_reason=capture_fault_reason(vector["preprocess_metrics"] or {}, baseline),
        )

        runner = BenchRunner(
            pipeline=PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json"),
            transport=_DeterministicTransport(scheduler_state="IDLE"),
            encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
            safety=BenchSafetyConfig(max_queue_age_ms=20.0, max_frame_staleness_ms=50.0),
            runtime_reject_thresholds=thresholds,
            capture_baseline_config=baseline,
        )
        tick = itertools.count(start=vector["perf_counter"][0], step=0.001)
        with patch("coloursorter.bench.runner.time.perf_counter", side_effect=lambda: next(tick)):
            log = runner.run_cycle(
                frame_id=frame.frame_id,
                timestamp_s=frame.timestamp_s,
                image_height_px=frame.image_height_px,
                image_width_px=frame.image_width_px,
                detections=[detection],
                previous_timestamp_s=0.9,
                enqueued_monotonic_s=vector["enqueued_monotonic_s"],
                captured_monotonic_s=vector["captured_monotonic_s"],
                preprocess_metrics=vector["preprocess_metrics"],
            )[0]

        assert log.decision == live_result.decisions[0].classification, vector["name"]
        assert log.rejection_reason == live_result.decisions[0].rejection_reason, vector["name"]
        assert log.scheduler_state == vector["expected_scheduler_state"], vector["name"]


def test_phase3_task35_production_equivalent_path_uses_transport_ack_without_synthetic_substitution() -> None:
    thresholds = _runtime_thresholds()
    detection = _build_detection(1.0)

    runner = BenchRunner(
        pipeline=PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json"),
        transport=_DeterministicTransport(scheduler_state="ARMED", ack_code="ACK"),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(send_budget_ms=10.0),
        runtime_reject_thresholds=thresholds,
        capture_baseline_config=CaptureBaselineConfig(),
    )

    tick = itertools.count(start=1.0, step=0.001)
    with patch("coloursorter.bench.runner.time.perf_counter", side_effect=lambda: next(tick)):
        log = runner.run_cycle(
            frame_id=36,
            timestamp_s=1.0,
            image_height_px=240,
            image_width_px=1100,
            detections=[detection],
            previous_timestamp_s=0.9,
        )[0]

    assert log.transport_sent is True
    assert log.ack_code == "ACK"
    assert log.scheduler_state == "ARMED"
    assert log.fault_event == ""
