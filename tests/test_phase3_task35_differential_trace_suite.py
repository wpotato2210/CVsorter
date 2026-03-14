from __future__ import annotations

import itertools
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

from coloursorter.bench.runner import BenchRunner, BenchSafetyConfig
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy import CaptureBaselineConfig, PipelineRunner, capture_fault_reason
from coloursorter.eval.reject_profiles import load_reject_profiles, selected_thresholds
from coloursorter.model import FrameMetadata, ObjectDetection


@dataclass(frozen=True)
class _FaultVector:
    name: str
    preprocess_metrics: dict[str, float | bool] | None
    enqueued_monotonic_s: float
    captured_monotonic_s: float
    now_s: float
    expected_scheduler_state: str


class _AckTransport:
    def __init__(self, scheduler_state: str = "IDLE", ack_code: str = "ACK") -> None:
        self._scheduler_state = scheduler_state
        self._ack_code = ack_code

    def send(self, _command: object) -> SimpleNamespace:
        return SimpleNamespace(
            queue_depth=0,
            scheduler_state=self._scheduler_state,
            mode="AUTO",
            queue_cleared=False,
            round_trip_ms=1.0,
            ack_code=self._ack_code,
            nack_code=None,
            nack_detail=None,
        )


def _thresholds() -> dict[str, float]:
    profiles, selected_name = load_reject_profiles("configs/reject_profiles.yaml")
    resolved = selected_thresholds(profiles, selected_name)
    return {name: float(resolved[name]) for name in sorted(resolved)}


def _reject_detection() -> ObjectDetection:
    return ObjectDetection(
        object_id="obj-3.5-diff",
        centroid_x_px=64.0,
        centroid_y_px=64.0,
        classification="reject",
        infection_score=1.0,
    )


def _run_trace_suite(vectors: tuple[_FaultVector, ...]) -> list[tuple[tuple[str, str | None], tuple[str, str | None, str]]]:
    frame = FrameMetadata(frame_id=135, timestamp_s=1.5, image_height_px=240, image_width_px=1100)
    detection = _reject_detection()
    thresholds = _thresholds()
    baseline = CaptureBaselineConfig()

    trace_pairs: list[tuple[tuple[str, str | None], tuple[str, str | None, str]]] = []
    for vector in vectors:
        live = PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json").run(
            frame=frame,
            detections=[detection],
            thresholds=thresholds,
            capture_fault_reason=capture_fault_reason(vector.preprocess_metrics or {}, baseline),
        )
        runner = BenchRunner(
            pipeline=PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json"),
            transport=_AckTransport(),
            encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
            safety=BenchSafetyConfig(max_queue_age_ms=20.0, max_frame_staleness_ms=50.0),
            runtime_reject_thresholds=thresholds,
            capture_baseline_config=baseline,
        )
        tick = itertools.count(start=vector.now_s, step=0.001)
        with patch("coloursorter.bench.runner.time.perf_counter", side_effect=lambda: next(tick)):
            bench_log = runner.run_cycle(
                frame_id=frame.frame_id,
                timestamp_s=frame.timestamp_s,
                image_height_px=frame.image_height_px,
                image_width_px=frame.image_width_px,
                detections=[detection],
                previous_timestamp_s=1.4,
                enqueued_monotonic_s=vector.enqueued_monotonic_s,
                captured_monotonic_s=vector.captured_monotonic_s,
                preprocess_metrics=vector.preprocess_metrics,
            )[0]

        live_trace = (live.decisions[0].classification, live.decisions[0].rejection_reason)
        bench_trace = (bench_log.decision, bench_log.rejection_reason, bench_log.scheduler_state)
        trace_pairs.append((live_trace, bench_trace))

        assert bench_log.scheduler_state == vector.expected_scheduler_state, vector.name
        assert live_trace[0] == bench_trace[0], vector.name
        assert live_trace[1] == bench_trace[1], vector.name

    return trace_pairs


def test_phase3_task35_differential_trace_suite_is_deterministic() -> None:
    vectors = (
        _FaultVector(
            name="capture_fault",
            preprocess_metrics={"preprocess_valid": False, "luma_after": 120.0},
            enqueued_monotonic_s=9.999,
            captured_monotonic_s=9.999,
            now_s=10.0,
            expected_scheduler_state="SKIPPED",
        ),
        _FaultVector(
            name="queue_age_fault",
            preprocess_metrics=None,
            enqueued_monotonic_s=19.8,
            captured_monotonic_s=19.999,
            now_s=20.0,
            expected_scheduler_state="SAFE",
        ),
        _FaultVector(
            name="frame_staleness_fault",
            preprocess_metrics=None,
            enqueued_monotonic_s=29.999,
            captured_monotonic_s=29.8,
            now_s=30.0,
            expected_scheduler_state="SAFE",
        ),
    )

    first_run = _run_trace_suite(vectors)
    second_run = _run_trace_suite(vectors)

    assert first_run == second_run
