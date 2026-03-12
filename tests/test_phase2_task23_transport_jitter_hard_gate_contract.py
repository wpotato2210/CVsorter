from __future__ import annotations

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs


def _entry(**overrides: object) -> BenchLogEntry:
    payload: dict[str, object] = {
        "run_id": "t23-run",
        "test_batch_id": "t23-batch",
        "event_timestamp_utc": "2024-01-01T00:00:00+00:00",
        "frame_timestamp_s": 0.0,
        "frame_id": 1,
        "object_id": "obj-1",
        "trigger_generation_s": 0.0,
        "lane": 1,
        "decision": "reject",
        "prediction_label": "reject",
        "confidence": 0.95,
        "rejection_reason": "classified_reject",
        "protocol_round_trip_ms": 4.0,
        "ack_code": AckCode.ACK,
        "actuator_command_issued": True,
        "transport_sent": True,
        "transport_acknowledged": True,
        "scheduler_window_missed": False,
        "rtt_jitter_ms": 7.0,
        "jitter_warn": True,
        "jitter_critical": True,
    }
    payload.update(overrides)
    return BenchLogEntry(**payload)


def test_phase2_task23_critical_jitter_alarm_is_non_blocking_within_scenario_limit() -> None:
    logs = (
        _entry(),
        _entry(frame_id=2, object_id="obj-2", frame_timestamp_s=0.1),
    )
    scenario = BenchScenario(
        "phase2",
        max_avg_rtt_ms=10.0,
        max_peak_rtt_ms=15.0,
        require_safe_transition=False,
        require_recovery=False,
        min_reject_reliability=0.99,
        max_jitter_ms=10.0,
        max_missed_window_count=0,
    )

    evaluation = evaluate_logs(logs, (scenario,))

    assert evaluation.summary["jitter_critical_alarm"] is True
    assert evaluation.summary["max_jitter_ms"] == 7.0
    assert evaluation.summary["reject_reliability"] == 1.0
    assert evaluation.summary["hard_gate_pass"] is True
