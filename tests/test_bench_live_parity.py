from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from coloursorter.bench.runner import BenchRunner
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy import CaptureBaselineConfig, PipelineRunner, capture_fault_reason
from coloursorter.eval.reject_profiles import load_reject_profiles, selected_thresholds
from coloursorter.model import DecisionPayload, FrameMetadata, ObjectDetection


def _runtime_thresholds() -> dict[str, float]:
    profiles, selected_name = load_reject_profiles(Path("configs/reject_profiles.yaml"))
    resolved = selected_thresholds(profiles, selected_name)
    return {key: float(resolved[key]) for key in sorted(resolved)}


def _decision_bytes(payload: DecisionPayload) -> bytes:
    as_payload = {
        "frame_id": payload.frame_id,
        "object_id": payload.object_id,
        "lane": payload.lane,
        "classification": payload.classification,
        "rejection_reason": payload.rejection_reason,
    }
    return json.dumps(as_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class _TransportStub:
    def send(self, _command):
        return SimpleNamespace(
            queue_depth=0,
            scheduler_state="IDLE",
            mode="AUTO",
            queue_cleared=False,
            round_trip_ms=1.0,
            ack_code="ACK",
            nack_code=None,
            nack_detail=None,
        )


def _build_bench_runner(thresholds: dict[str, float]) -> BenchRunner:
    return BenchRunner(
        pipeline=PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json"),
        transport=_TransportStub(),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        runtime_reject_thresholds=thresholds,
        capture_baseline_config=CaptureBaselineConfig(),
    )


def test_bench_and_live_pipeline_emit_identical_threshold_boundary_decision_bytes() -> None:
    thresholds = _runtime_thresholds()
    frame = FrameMetadata(frame_id=41, timestamp_s=1.0, image_height_px=240, image_width_px=1100)
    infection_threshold = thresholds["rot"] * 0.01
    detection = ObjectDetection(
        object_id="obj-boundary",
        centroid_x_px=80.0,
        centroid_y_px=80.0,
        classification="accept",
        infection_score=infection_threshold,
    )

    live_pipeline = PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json")
    live_result = live_pipeline.run(frame=frame, detections=[detection], thresholds=thresholds, capture_fault_reason=None)

    bench_log = _build_bench_runner(thresholds).run_cycle(
        frame_id=frame.frame_id,
        timestamp_s=frame.timestamp_s,
        image_height_px=frame.image_height_px,
        image_width_px=frame.image_width_px,
        detections=[detection],
        previous_timestamp_s=0.9,
    )[0]

    bench_payload = DecisionPayload(
        frame_id=bench_log.frame_id,
        object_id=bench_log.object_id,
        lane=bench_log.lane,
        centroid_mm=live_result.decisions[0].centroid_mm,
        trigger_mm=live_result.decisions[0].trigger_mm,
        classification=bench_log.decision,
        rejection_reason=bench_log.rejection_reason,
    )

    assert _decision_bytes(bench_payload) == _decision_bytes(live_result.decisions[0])


def test_capture_fault_context_precedence_matches_live_contract() -> None:
    thresholds = _runtime_thresholds()
    frame = FrameMetadata(frame_id=42, timestamp_s=2.0, image_height_px=240, image_width_px=1100)
    detection = ObjectDetection(
        object_id="obj-fault",
        centroid_x_px=80.0,
        centroid_y_px=80.0,
        classification="reject",
        infection_score=1.0,
    )
    preprocess_metrics = {"preprocess_valid": False, "luma_after": 120.0}
    baseline = CaptureBaselineConfig()
    capture_fault = capture_fault_reason(preprocess_metrics, baseline)

    live_pipeline = PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json")
    live_result = live_pipeline.run(
        frame=frame,
        detections=[detection],
        thresholds=thresholds,
        capture_fault_reason=capture_fault,
    )

    bench_log = BenchRunner(
        pipeline=PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json"),
        transport=_TransportStub(),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        runtime_reject_thresholds=thresholds,
        capture_baseline_config=baseline,
    ).run_cycle(
        frame_id=frame.frame_id,
        timestamp_s=frame.timestamp_s,
        image_height_px=frame.image_height_px,
        image_width_px=frame.image_width_px,
        detections=[detection],
        previous_timestamp_s=1.9,
        preprocess_metrics=preprocess_metrics,
    )[0]

    assert live_result.decisions[0].classification == "unknown"
    assert live_result.decisions[0].rejection_reason == "capture_preprocess_invalid"
    assert bench_log.decision == live_result.decisions[0].classification
    assert bench_log.rejection_reason == live_result.decisions[0].rejection_reason
