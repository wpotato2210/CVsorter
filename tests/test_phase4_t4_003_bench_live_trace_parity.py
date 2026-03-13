from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from coloursorter.bench.runner import BenchRunner
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy import CaptureBaselineConfig, PipelineRunner, capture_fault_reason
from coloursorter.eval.reject_profiles import load_reject_profiles, selected_thresholds
from coloursorter.model import FrameMetadata, ObjectDetection

_FIXTURE = Path(__file__).parent / "fixtures" / "bench_live_trace_t4_003.json"


class _TransportStub:
    def send(self, _command: Any) -> SimpleNamespace:
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


def _runtime_thresholds() -> dict[str, float]:
    profiles, selected_name = load_reject_profiles(Path("configs/reject_profiles.yaml"))
    resolved = selected_thresholds(profiles, selected_name)
    return {key: float(resolved[key]) for key in sorted(resolved)}


def _run_bench_trace(
    frame: FrameMetadata,
    detection: ObjectDetection,
    thresholds: dict[str, float],
    preprocess_metrics: dict[str, float | bool] | None,
) -> dict[str, str | None]:
    log = BenchRunner(
        pipeline=PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json"),
        transport=_TransportStub(),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        runtime_reject_thresholds=thresholds,
        capture_baseline_config=CaptureBaselineConfig(),
    ).run_cycle(
        frame_id=frame.frame_id,
        timestamp_s=frame.timestamp_s,
        image_height_px=frame.image_height_px,
        image_width_px=frame.image_width_px,
        detections=[detection],
        previous_timestamp_s=max(0.0, frame.timestamp_s - 0.1),
        preprocess_metrics=preprocess_metrics,
    )[0]
    return {
        "decision": log.decision,
        "rejection_reason": log.rejection_reason,
        "mode": log.mode,
        "scheduler_state": log.scheduler_state,
    }


def _run_live_trace(
    frame: FrameMetadata,
    detection: ObjectDetection,
    thresholds: dict[str, float],
    preprocess_metrics: dict[str, float | bool] | None,
) -> dict[str, str | None]:
    baseline = CaptureBaselineConfig()
    result = PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json").run(
        frame=frame,
        detections=[detection],
        thresholds=thresholds,
        capture_fault_reason=capture_fault_reason(preprocess_metrics or {}, baseline),
    )
    decision = result.decisions[0]
    event = result.scheduled_events[0] if result.scheduled_events else None

    response = _TransportStub().send(event.command) if event is not None else SimpleNamespace(mode="AUTO", scheduler_state="SKIPPED")
    return {
        "decision": decision.classification,
        "rejection_reason": decision.rejection_reason,
        "mode": response.mode,
        "scheduler_state": response.scheduler_state,
    }


def test_t4_003_bench_live_differential_trace_fields_match_fixture_vectors() -> None:
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    thresholds = _runtime_thresholds()
    boundary_score = thresholds["rot"] * 0.01

    for vector in payload["vectors"]:
        frame = FrameMetadata(**vector["frame"])
        detection = ObjectDetection(
            object_id=vector["detection"]["object_id"],
            centroid_x_px=vector["detection"]["centroid_x_px"],
            centroid_y_px=vector["detection"]["centroid_y_px"],
            classification=vector["detection"]["classification"],
            infection_score=boundary_score + float(vector["detection"]["infection_score_delta"]),
        )
        preprocess_metrics = vector["preprocess_metrics"]

        bench_trace = _run_bench_trace(frame, detection, thresholds, preprocess_metrics)
        live_trace = _run_live_trace(frame, detection, thresholds, preprocess_metrics)

        assert bench_trace == live_trace
        assert bench_trace["decision"] == vector["expected"]["decision"]
        assert bench_trace["rejection_reason"] == vector["expected"]["rejection_reason"]
