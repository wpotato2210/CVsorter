from __future__ import annotations

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs


def _entry(*, frame_id: int, object_id: str, scheduler_window_missed: bool) -> BenchLogEntry:
    return BenchLogEntry(
        run_id="r-task27",
        test_batch_id="b-task27",
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


def test_phase2_task27_hard_gate_fails_above_missed_window_boundary() -> None:
    logs = (
        _entry(frame_id=1, object_id="obj-1", scheduler_window_missed=False),
        _entry(frame_id=2, object_id="obj-2", scheduler_window_missed=True),
    )

    evaluation = evaluate_logs(logs, (BenchScenario("phase2", 10.0, 15.0, False, False),))

    assert evaluation.summary["missed_window_count"] == 1
    assert evaluation.summary["hard_gate_pass"] is False
