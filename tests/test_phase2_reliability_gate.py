from __future__ import annotations

import json

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs, write_artifacts


def _entry(**overrides: object) -> BenchLogEntry:
    payload: dict[str, object] = {
        "run_id": "r2",
        "test_batch_id": "b2",
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
    }
    payload.update(overrides)
    return BenchLogEntry(**payload)


def test_hard_gate_passes_for_nominal_chain() -> None:
    evaluation = evaluate_logs((_entry(), _entry(frame_id=2, object_id="obj-2", frame_timestamp_s=0.1)), (
        BenchScenario("phase2", 10.0, 15.0, False, False),
    ))

    assert evaluation.summary["hard_gate_pass"] is True
    assert evaluation.summary["reject_reliability"] == 1.0


def test_hard_gate_fails_for_missed_window_or_jitter() -> None:
    logs = (
        _entry(rtt_jitter_ms=1.0),
        _entry(frame_id=2, object_id="obj-2", transport_acknowledged=False, actuator_command_issued=False),
        _entry(frame_id=3, object_id="obj-3", scheduler_window_missed=True, rtt_jitter_ms=12.0),
    )

    evaluation = evaluate_logs(logs, (BenchScenario("phase2", 10.0, 15.0, False, False),))

    assert evaluation.summary["hard_gate_pass"] is False
    assert evaluation.summary["reject_reliability"] < 1.0
    assert evaluation.summary["missed_window_count"] == 1


def test_write_artifacts_emits_audit_trail_file(tmp_path) -> None:
    logs = (_entry(),)
    evaluation = evaluate_logs(logs, (BenchScenario("phase2", 10.0, 15.0, False, False),))
    audit = (
        {"event": "recipe_selection", "camera_recipe": "cam-a"},
        {"event": "operator_action", "command": "recover_to_auto"},
    )

    artifact_dir = write_artifacts(logs, evaluation, tmp_path, include_text_report=False, audit_trail=audit)

    lines = (artifact_dir / "audit_trail.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "recipe_selection"
