from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from coloursorter.bench.runner import BenchRunner, BenchSafetyConfig
from coloursorter.bench.types import AckCode
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy.pipeline import PipelineResult, ScheduledDecision
from coloursorter.model import CentroidMM, DecisionPayload, ObjectDetection
from coloursorter.scheduler import build_scheduled_command


FIXTURE_PATH = Path("tests/fixtures/timing_drift_t4_004.json")


class _PipelineStub:
    def __init__(self) -> None:
        decision = DecisionPayload(
            frame_id=1,
            object_id="det-1",
            lane=0,
            centroid_mm=CentroidMM(x_mm=1.0, y_mm=1.0),
            trigger_mm=100.0,
            classification="reject",
            rejection_reason="rule_threshold",
        )
        command = build_scheduled_command(0, 100.0)
        self._result = PipelineResult(
            decisions=(decision,),
            schedule_commands=(command,),
            scheduled_events=(ScheduledDecision("det-1", decision, command),),
        )

    def run(self, frame, detections):
        return self._result


class _AckTransportSequenceStub:
    def __init__(self, round_trip_ms_values: Sequence[float]) -> None:
        self._round_trip_ms_values = list(round_trip_ms_values)
        self._index = 0

    def send(self, _command):
        round_trip_ms = self._round_trip_ms_values[min(self._index, len(self._round_trip_ms_values) - 1)]
        self._index += 1

        class _Response:
            queue_depth = 0
            scheduler_state = "IDLE"
            mode = "AUTO"
            queue_cleared = False
            ack_code = AckCode.ACK
            nack_code = None
            nack_detail = None

        response = _Response()
        response.round_trip_ms = round_trip_ms
        return response


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return payload


def _run_vector(round_trip_ms_values: Sequence[float], warn_ms: float, critical_ms: float) -> tuple[tuple[float, bool, bool], ...]:
    runner = BenchRunner(
        pipeline=_PipelineStub(),
        transport=_AckTransportSequenceStub(round_trip_ms_values),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(jitter_warn_ms=warn_ms, jitter_critical_ms=critical_ms),
    )

    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    results: list[tuple[float, bool, bool]] = []
    previous_timestamp_s = 0.9
    for cycle_index, _ in enumerate(round_trip_ms_values, start=1):
        logs = runner.run_cycle(
            frame_id=cycle_index,
            timestamp_s=1.0 + (cycle_index * 0.1),
            image_height_px=20,
            image_width_px=20,
            detections=[detection],
            previous_timestamp_s=previous_timestamp_s,
        )
        previous_timestamp_s = 1.0 + (cycle_index * 0.1)
        results.append((logs[0].rtt_jitter_ms, logs[0].jitter_warn, logs[0].jitter_critical))

    return tuple(results)


def test_t4_004_fixture_has_deterministic_vector_order_and_seed() -> None:
    payload = _load_fixture()
    assert payload["vector_pack"] == "T4-004"
    assert payload["seed"] == 4004

    vectors = payload["vectors"]
    assert [vector["id"] for vector in vectors] == [
        "stable_within_window",
        "warn_window_crossed",
        "critical_window_crossed",
    ]


def test_t4_004_replay_jitter_drift_harness_is_deterministic_and_windowed() -> None:
    payload = _load_fixture()
    warn_ms = float(payload["drift_window_ms"]["warn"])
    critical_ms = float(payload["drift_window_ms"]["critical"])

    for vector in payload["vectors"]:
        observed_once = _run_vector(vector["round_trip_ms"], warn_ms, critical_ms)
        observed_twice = _run_vector(vector["round_trip_ms"], warn_ms, critical_ms)

        assert observed_once == observed_twice

        drift_values = [round(drift_ms, 3) for drift_ms, _, _ in observed_once]
        warn_flags = [warn for _, warn, _ in observed_once]
        critical_flags = [critical for _, _, critical in observed_once]

        expected_drift = [round(float(item), 3) for item in vector["expected_drift_ms"]]
        expected_warn = [bool(item) for item in vector["expected_warn"]]
        expected_critical = [bool(item) for item in vector["expected_critical"]]

        assert drift_values == expected_drift
        assert warn_flags == expected_warn
        assert critical_flags == expected_critical

        vector_pass = not any(critical_flags)
        assert vector_pass is bool(vector["expected_pass"])
