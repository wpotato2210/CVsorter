from __future__ import annotations

import json
from pathlib import Path

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs
from coloursorter.bench.scenarios import BenchSummary


VECTOR_FIXTURE_PATH = Path("tests/fixtures/timing_jitter_t3_002.json")
SNAPSHOT_FIXTURE_PATH = Path("tests/fixtures/timing_jitter_t3_002_report_snapshot.json")


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


def _load_vectors_fixture() -> dict[str, object]:
    payload = json.loads(VECTOR_FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return payload


def _build_report() -> list[dict[str, object]]:
    payload = _load_vectors_fixture()
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

    report: list[dict[str, object]] = []
    for vector in payload["vectors"]:
        target_reliability = float(vector["reject_reliability"])
        expected_rejects = 1000
        successful_rejects = int(target_reliability * expected_rejects)

        logs = tuple(
            BenchLogEntry(
                **{
                    **_entry(jitter_ms=0.0, scheduler_window_missed=False).__dict__,
                    "transport_sent": index < successful_rejects,
                    "transport_acknowledged": index < successful_rejects,
                    "actuator_command_issued": index < successful_rejects,
                    "rtt_jitter_ms": float(vector["max_jitter_ms"]) if index == 0 else 0.0,
                    "scheduler_window_missed": bool(vector["missed_window_count"]) and index == expected_rejects - 1,
                }
            )
            for index in range(expected_rejects)
        )

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

        evaluation = evaluate_logs(logs=logs, scenarios=(scenario,))
        scenario_result = scenario.evaluate(summary)

        report.append(
            {
                "id": str(vector["id"]),
                "scenario_pass": scenario_result.passed,
                "hard_gate_pass": bool(evaluation.summary["hard_gate_pass"]),
                "reject_reliability": float(evaluation.summary["reject_reliability"]),
                "max_jitter_ms": float(evaluation.summary["max_jitter_ms"]),
                "missed_window_count": int(evaluation.summary["missed_window_count"]),
            }
        )

    return report


def test_t3_002_timing_jitter_report_snapshot_is_stable() -> None:
    expected = json.loads(SNAPSHOT_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert _build_report() == expected["report"]
