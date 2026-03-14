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

FIXTURE_PATH = Path("tests/fixtures/bench_live_parity_t3_005.json")


class _ReplayTransport:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response

    def send(self, _command: Any) -> SimpleNamespace:
        return SimpleNamespace(
            queue_depth=int(self._response["queue_depth"]),
            scheduler_state=str(self._response["scheduler_state"]),
            mode=str(self._response["mode"]),
            queue_cleared=bool(self._response["queue_cleared"]),
            round_trip_ms=float(self._response["round_trip_ms"]),
            ack_code=str(self._response["ack_code"]),
            nack_code=None,
            nack_detail=None,
        )


def _runtime_thresholds() -> dict[str, float]:
    profiles, selected_name = load_reject_profiles(Path("configs/reject_profiles.yaml"))
    resolved = selected_thresholds(profiles, selected_name)
    return {key: float(resolved[key]) for key in sorted(resolved)}


def _bench_trace(
    frame: FrameMetadata,
    detection: ObjectDetection,
    thresholds: dict[str, float],
    preprocess_metrics: dict[str, float | bool] | None,
    transport_response: dict[str, object],
) -> dict[str, str | int | bool | None]:
    log = BenchRunner(
        pipeline=PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json"),
        transport=_ReplayTransport(transport_response),
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
        "queue_depth": log.queue_depth,
        "scheduler_state": log.scheduler_state,
        "queue_cleared": log.queue_cleared,
    }


def _live_trace(
    frame: FrameMetadata,
    detection: ObjectDetection,
    thresholds: dict[str, float],
    preprocess_metrics: dict[str, float | bool] | None,
    transport_response: dict[str, object],
) -> dict[str, str | int | bool | None]:
    baseline = CaptureBaselineConfig()
    result = PipelineRunner("configs/lane_geometry.yaml", "configs/calibration.json").run(
        frame=frame,
        detections=[detection],
        thresholds=thresholds,
        capture_fault_reason=capture_fault_reason(preprocess_metrics or {}, baseline),
    )

    decision = result.decisions[0]
    scheduled_event = result.scheduled_events[0] if result.scheduled_events else None
    if scheduled_event is None:
        return {
            "decision": decision.classification,
            "rejection_reason": decision.rejection_reason,
            "mode": "AUTO",
            "queue_depth": 0,
            "scheduler_state": "SKIPPED",
            "queue_cleared": False,
        }

    response = _ReplayTransport(transport_response).send(scheduled_event.command)
    return {
        "decision": decision.classification,
        "rejection_reason": decision.rejection_reason,
        "mode": str(response.mode),
        "queue_depth": int(response.queue_depth),
        "scheduler_state": str(response.scheduler_state),
        "queue_cleared": bool(response.queue_cleared),
    }


def test_t3_005_fixture_is_seeded_and_ordered() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert payload["vector_pack"] == "T3-005"
    assert payload["seed"] == 3005
    names = [str(vector["name"]) for vector in payload["vectors"]]
    assert names == ["reject_command_ack_path", "capture_fault_skip_path"]


def test_t3_005_bench_and_live_parity_trace_vectors_are_identical() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    thresholds = _runtime_thresholds()
    boundary_score = thresholds["rot"] * 0.01

    previous_scheduler_state = "IDLE"
    for vector in payload["vectors"]:
        frame = FrameMetadata(**vector["frame"])
        detection = ObjectDetection(
            object_id=vector["detection"]["object_id"],
            centroid_x_px=float(vector["detection"]["centroid_x_px"]),
            centroid_y_px=float(vector["detection"]["centroid_y_px"]),
            classification=str(vector["detection"]["classification"]),
            infection_score=boundary_score + float(vector["detection"]["infection_score_delta"]),
        )
        preprocess_metrics = vector["preprocess_metrics"]
        transport_response = vector["transport_response"]

        bench_trace = _bench_trace(frame, detection, thresholds, preprocess_metrics, transport_response)
        live_trace = _live_trace(frame, detection, thresholds, preprocess_metrics, transport_response)

        assert bench_trace == live_trace
        assert bench_trace["decision"] == vector["expected"]["decision"]
        assert bench_trace["rejection_reason"] == vector["expected"]["rejection_reason"]
        assert bench_trace["mode"] == vector["expected"]["mode"]
        assert bench_trace["queue_depth"] == vector["expected"]["queue_depth"]
        assert bench_trace["scheduler_state"] == vector["expected"]["scheduler_state"]
        assert bench_trace["queue_cleared"] is vector["expected"]["queue_cleared"]

        transition = f"{previous_scheduler_state}->{bench_trace['scheduler_state']}"
        assert transition == vector["expected"]["scheduler_transition"]
        previous_scheduler_state = str(bench_trace["scheduler_state"])
