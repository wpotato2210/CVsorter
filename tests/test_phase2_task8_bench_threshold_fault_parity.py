from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from coloursorter.bench.runner import BenchRunner
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy import CaptureBaselineConfig, PipelineResult, PipelineRunner, capture_fault_reason
from coloursorter.eval.reject_profiles import load_reject_profiles, selected_thresholds
from coloursorter.model import FrameMetadata, ObjectDetection


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


class _PipelineSpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(
        self,
        frame: FrameMetadata,
        detections: list[ObjectDetection],
        thresholds: dict[str, float] | None = None,
        capture_fault_reason: str | None = None,
    ) -> PipelineResult:
        self.calls.append(
            {
                "frame": frame,
                "detections": detections,
                "thresholds": thresholds,
                "capture_fault_reason": capture_fault_reason,
            }
        )
        return PipelineResult(decisions=(), schedule_commands=(), scheduled_events=())


def _runtime_thresholds() -> dict[str, float]:
    profiles, selected_name = load_reject_profiles(Path("configs/reject_profiles.yaml"))
    resolved = selected_thresholds(profiles, selected_name)
    return {key: float(resolved[key]) for key in sorted(resolved)}


def _decision_bytes(frame_id: int, object_id: str, lane: int, classification: str, rejection_reason: str | None) -> bytes:
    payload = {
        "frame_id": frame_id,
        "object_id": object_id,
        "lane": lane,
        "classification": classification,
        "rejection_reason": rejection_reason,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _run_bench(
    *,
    thresholds: dict[str, float],
    frame: FrameMetadata,
    detection: ObjectDetection,
    preprocess_metrics: dict[str, float | bool] | None,
) -> tuple[str, str | None, bytes]:
    bench_log = BenchRunner(
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
    decision_bytes = _decision_bytes(
        frame_id=bench_log.frame_id,
        object_id=bench_log.object_id,
        lane=bench_log.lane,
        classification=bench_log.decision,
        rejection_reason=bench_log.rejection_reason,
    )
    return bench_log.decision, bench_log.rejection_reason, decision_bytes


def _run_live(
    *,
    thresholds: dict[str, float],
    frame: FrameMetadata,
    detection: ObjectDetection,
    preprocess_metrics: dict[str, float | bool] | None,
) -> tuple[str, str | None, bytes]:
    baseline = CaptureBaselineConfig()
    live_result = PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json").run(
        frame=frame,
        detections=[detection],
        thresholds=thresholds,
        capture_fault_reason=capture_fault_reason(preprocess_metrics or {}, baseline),
    )
    decision = live_result.decisions[0]
    decision_bytes = _decision_bytes(
        frame_id=decision.frame_id,
        object_id=decision.object_id,
        lane=decision.lane,
        classification=decision.classification,
        rejection_reason=decision.rejection_reason,
    )
    return decision.classification, decision.rejection_reason, decision_bytes


def test_phase2_task8_bench_runner_passes_runtime_thresholds_and_capture_fault_context() -> None:
    thresholds = _runtime_thresholds()
    preprocess_metrics = {"preprocess_valid": False, "luma_after": 120.0}

    pipeline_spy = _PipelineSpy()
    runner = BenchRunner(
        pipeline=pipeline_spy,
        transport=_TransportStub(),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        runtime_reject_thresholds=thresholds,
        capture_baseline_config=CaptureBaselineConfig(),
    )

    runner.run_cycle(
        frame_id=1,
        timestamp_s=1.0,
        image_height_px=240,
        image_width_px=1100,
        detections=[],
        previous_timestamp_s=0.9,
        preprocess_metrics=preprocess_metrics,
    )

    assert len(pipeline_spy.calls) == 1
    call = pipeline_spy.calls[0]
    assert call["thresholds"] == thresholds
    assert call["capture_fault_reason"] == "capture_preprocess_invalid"


@pytest.mark.parametrize(
    ("object_id", "infection_score", "classification", "preprocess_metrics", "expected_decision", "expected_reason"),
    (
        ("obj-threshold-boundary", 0.0, "accept", None, "reject", "infection_score_threshold"),
        (
            "obj-fault-precedence",
            0.0,
            "reject",
            {"preprocess_valid": False, "luma_after": 120.0},
            "unknown",
            "capture_preprocess_invalid",
        ),
    ),
)
def test_phase2_task8_bench_and_live_reason_codes_are_identical_for_fixed_fixtures(
    object_id: str,
    infection_score: float,
    classification: str,
    preprocess_metrics: dict[str, float | bool] | None,
    expected_decision: str,
    expected_reason: str,
) -> None:
    thresholds = _runtime_thresholds()
    threshold_boundary_score = thresholds["rot"] * 0.01
    frame = FrameMetadata(frame_id=81, timestamp_s=1.0, image_height_px=240, image_width_px=1100)
    detection = ObjectDetection(
        object_id=object_id,
        centroid_x_px=80.0,
        centroid_y_px=80.0,
        classification=classification,
        infection_score=threshold_boundary_score + infection_score,
    )

    bench_decision, bench_reason, bench_bytes = _run_bench(
        thresholds=thresholds,
        frame=frame,
        detection=detection,
        preprocess_metrics=preprocess_metrics,
    )
    live_decision, live_reason, live_bytes = _run_live(
        thresholds=thresholds,
        frame=frame,
        detection=detection,
        preprocess_metrics=preprocess_metrics,
    )

    assert bench_decision == expected_decision
    assert bench_reason == expected_reason
    assert live_decision == expected_decision
    assert live_reason == expected_reason
    assert bench_bytes == live_bytes
