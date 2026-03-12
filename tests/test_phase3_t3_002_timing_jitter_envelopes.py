from __future__ import annotations

import json
from pathlib import Path

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs
from coloursorter.bench.scenarios import BenchSummary


FIXTURE_PATH = Path("tests/fixtures/timing_jitter_t3_002.json")


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return payload


def _entry(*, jitter_ms: float, scheduler_window_missed: bool) -> BenchLogEntry:
    return BenchLogEntry(
        run_id="t3-002",
        test_batch_id="timing-jitter-envelope",
        event_timestamp_utc="2024-01-01T00:00:00+00:00",
        frame_timestamp_s=0.0,
        frame_id=1,
        object_id="obj-1",
        trigger_generation_s=0.0,
        lane=0,
        decision="reject",
        prediction_label="reject",
        confidence=1.0,
        rejection_reason="deterministic_test",
        protocol_round_trip_ms=5.0,
        ack_code=AckCode.ACK,
        transport_sent=not scheduler_window_missed,
        transport_acknowledged=not scheduler_window_missed,
        actuator_command_issued=not scheduler_window_missed,
        rtt_jitter_ms=jitter_ms,
        scheduler_window_missed=scheduler_window_missed,
    )


def test_t3_002_fixture_has_deterministic_vector_order_and_seed() -> None:
    payload = _load_fixture()
    assert payload["vector_pack"] == "T3-002"
    assert payload["seed"] == 3002

    vectors = payload["vectors"]
    vector_ids = [vector["id"] for vector in vectors]
    assert vector_ids == [
        "inside_envelope",
        "edge_envelope",
        "outside_jitter",
        "outside_missed_window",
        "outside_reliability",
    ]


def test_t3_002_timing_jitter_envelope_boundaries() -> None:
    payload = _load_fixture()
    envelope = payload["envelope"]

    scenario = BenchScenario(
        name="t3-002-jitter-envelope",
        max_avg_rtt_ms=25.0,
        max_peak_rtt_ms=60.0,
        require_safe_transition=False,
        require_recovery=False,
        min_reject_reliability=float(envelope["min_reject_reliability"]),
        max_jitter_ms=float(envelope["max_jitter_ms"]),
        max_missed_window_count=int(envelope["max_missed_window_count"]),
    )

    for vector in payload["vectors"]:
        summary = BenchSummary(
            avg_round_trip_ms=5.0,
            max_round_trip_ms=5.0,
            safe_transitions=0,
            watchdog_transitions=0,
            recovered_from_safe=False,
            reject_reliability=float(vector["reject_reliability"]),
            max_jitter_ms=float(vector["max_jitter_ms"]),
            missed_window_count=int(vector["missed_window_count"]),
        )

        scenario_result = scenario.evaluate(summary)
        assert scenario_result.passed is bool(vector["expected_pass"])

        target_reliability = float(vector["reject_reliability"])
        expected_rejects = 1000
        successful_rejects = int(target_reliability * expected_rejects)

        logs = tuple(
            _entry(jitter_ms=0.0, scheduler_window_missed=False)
            for _ in range(successful_rejects)
        ) + tuple(
            _entry(jitter_ms=0.0, scheduler_window_missed=False,)
            for _ in range(expected_rejects - successful_rejects)
        )

        logs = tuple(
            BenchLogEntry(
                **{
                    **entry.__dict__,
                    "transport_sent": i < successful_rejects,
                    "transport_acknowledged": i < successful_rejects,
                    "actuator_command_issued": i < successful_rejects,
                    "rtt_jitter_ms": float(vector["max_jitter_ms"]) if i == 0 else 0.0,
                    "scheduler_window_missed": bool(vector["missed_window_count"]) and i == expected_rejects - 1,
                }
            )
            for i, entry in enumerate(logs)
        )

        evaluation = evaluate_logs(logs=logs, scenarios=(scenario,))
        assert evaluation.summary["hard_gate_pass"] is bool(vector["expected_hard_gate_pass"])
