from __future__ import annotations

import ast
from pathlib import Path

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs


def _entry(*, frame_id: int, object_id: str, rtt_jitter_ms: float) -> BenchLogEntry:
    return BenchLogEntry(
        run_id="r-task24",
        test_batch_id="b-task24",
        event_timestamp_utc="2024-01-01T00:00:00+00:00",
        frame_timestamp_s=frame_id / 10.0,
        frame_id=frame_id,
        object_id=object_id,
        trigger_generation_s=0.0,
        lane=1,
        decision="reject",
        prediction_label="reject",
        confidence=0.95,
        rejection_reason="classified_reject",
        protocol_round_trip_ms=4.0,
        ack_code=AckCode.ACK,
        actuator_command_issued=True,
        transport_sent=True,
        transport_acknowledged=True,
        scheduler_window_missed=False,
        rtt_jitter_ms=rtt_jitter_ms,
        jitter_warn=rtt_jitter_ms >= 5.0,
        jitter_critical=rtt_jitter_ms >= 10.0,
    )


def test_phase2_task24_hard_gate_allows_equal_jitter_boundary() -> None:
    logs = (
        _entry(frame_id=1, object_id="obj-1", rtt_jitter_ms=1.0),
        _entry(frame_id=2, object_id="obj-2", rtt_jitter_ms=10.0),
    )

    evaluation = evaluate_logs(logs, (BenchScenario("phase2", 10.0, 15.0, False, False),))

    assert evaluation.summary["max_jitter_ms"] == 10.0
    assert evaluation.summary["jitter_critical_alarm"] is True
    assert evaluation.summary["hard_gate_pass"] is True


def test_phase2_task24_hard_gate_uses_less_equal_jitter_guard() -> None:
    source = Path("src/coloursorter/bench/evaluation.py").read_text(encoding="utf-8")
    module = ast.parse(source)

    found_less_equal_guard = False

    for node in ast.walk(module):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            left_text = ast.unparse(node.left)
            right_text = ast.unparse(node.comparators[0])
            if left_text == "bench_summary.max_jitter_ms" and right_text == "10.0":
                found_less_equal_guard = True

    assert found_less_equal_guard is True
