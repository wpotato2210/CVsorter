from __future__ import annotations

import ast
from pathlib import Path

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs


def _entry(*, frame_id: int, object_id: str, scheduler_window_missed: bool) -> BenchLogEntry:
    return BenchLogEntry(
        run_id="r-task26",
        test_batch_id="b-task26",
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
        scheduler_window_missed=scheduler_window_missed,
        rtt_jitter_ms=1.0,
        jitter_warn=False,
        jitter_critical=False,
    )


def test_phase2_task26_hard_gate_allows_zero_missed_windows_boundary() -> None:
    logs = (
        _entry(frame_id=1, object_id="obj-1", scheduler_window_missed=False),
        _entry(frame_id=2, object_id="obj-2", scheduler_window_missed=False),
    )

    evaluation = evaluate_logs(logs, (BenchScenario("phase2", 10.0, 15.0, False, False),))

    assert evaluation.summary["missed_window_count"] == 0
    assert evaluation.summary["hard_gate_pass"] is True


def test_phase2_task26_hard_gate_uses_zero_missed_window_equality_guard() -> None:
    source = Path("src/coloursorter/bench/evaluation.py").read_text(encoding="utf-8")
    module = ast.parse(source)

    found_zero_equality_guard = False

    for node in ast.walk(module):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left_text = ast.unparse(node.left)
            right_text = ast.unparse(node.comparators[0])
            if left_text == "bench_summary.missed_window_count" and right_text == "0":
                found_zero_equality_guard = True

    assert found_zero_equality_guard is True
