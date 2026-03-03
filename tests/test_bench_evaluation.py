from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs, write_artifacts


def _entry(**overrides: object) -> BenchLogEntry:
    payload: dict[str, object] = {
        "run_id": "r1",
        "test_batch_id": "b1",
        "event_timestamp_utc": "2024-01-01T00:00:00+00:00",
        "frame_timestamp_s": 0.0,
        "frame_id": 1,
        "object_id": "obj-1",
        "trigger_generation_s": 0.0,
        "lane": 0,
        "decision": "accept",
        "prediction_label": "accept",
        "confidence": 0.5,
        "rejection_reason": None,
        "protocol_round_trip_ms": 10.0,
        "ack_code": AckCode.ACK,
    }
    payload.update(overrides)
    return BenchLogEntry(**payload)


def test_evaluate_logs_applies_scenarios() -> None:
    logs = (
        _entry(frame_timestamp_s=0.0, protocol_round_trip_ms=10.0),
        _entry(frame_timestamp_s=0.1, frame_id=2, object_id="obj-2", protocol_round_trip_ms=12.0),
    )
    scenarios = (
        BenchScenario("tight", max_avg_rtt_ms=11.0, max_peak_rtt_ms=15.0, require_safe_transition=False, require_recovery=False),
    )

    evaluation = evaluate_logs(logs, scenarios)

    assert evaluation.passed
    assert evaluation.summary["avg_round_trip_ms"] == 11.0
    assert evaluation.summary["p50_round_trip_ms"] == 11.0
    assert evaluation.summary["p95_round_trip_ms"] == pytest.approx(11.9)
    assert evaluation.summary["p99_round_trip_ms"] == pytest.approx(11.98)
    assert evaluation.scenarios[0].name == "tight"


def test_write_artifacts_writes_summary_and_telemetry(tmp_path: Path) -> None:
    logs = (
        _entry(decision="reject", prediction_label="reject", rejection_reason="rule", protocol_round_trip_ms=6.5, ack_code=AckCode.NACK_SAFE),
    )
    scenarios = (
        BenchScenario("fault", max_avg_rtt_ms=8.0, max_peak_rtt_ms=10.0, require_safe_transition=True, require_recovery=False),
    )
    evaluation = evaluate_logs(logs, scenarios)

    artifact_dir = write_artifacts(logs, evaluation, tmp_path, include_text_report=True, config_snapshot={"a": 1})

    summary_payload = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    telemetry_lines = (artifact_dir / "telemetry.csv").read_text(encoding="utf-8").strip().splitlines()

    assert summary_payload["passed"] is True
    assert summary_payload["scenarios"][0]["name"] == "fault"
    assert len(telemetry_lines) == 2
    assert (artifact_dir / "report.txt").exists()
    assert (artifact_dir / "events.jsonl").exists()
    assert (artifact_dir / "config_snapshot.json").exists()


def test_telemetry_csv_includes_required_openspec_v3_fields(tmp_path: Path) -> None:
    logs = (
        _entry(
            frame_timestamp_s=0.2,
            trigger_generation_s=0.2,
            lane=2,
            decision="reject",
            prediction_label="reject",
            rejection_reason="classified_reject",
            protocol_round_trip_ms=5.0,
            ack_code=AckCode.ACK,
            trigger_timestamp_s=0.2,
            trigger_mm=304.6,
            lane_index=2,
            belt_speed_mm_s=300.0,
            queue_depth=1,
            scheduler_state="ACTIVE",
            mode="AUTO",
        ),
    )
    scenarios = (
        BenchScenario("nominal", max_avg_rtt_ms=20.0, max_peak_rtt_ms=20.0, require_safe_transition=False, require_recovery=False),
    )
    evaluation = evaluate_logs(logs, scenarios)

    artifact_dir = write_artifacts(logs, evaluation, tmp_path, include_text_report=False)
    header = (artifact_dir / "telemetry.csv").read_text(encoding="utf-8").splitlines()[0].split(",")

    assert header[:6] == [
        "run_id",
        "test_batch_id",
        "event_timestamp_utc",
        "frame_timestamp",
        "frame_id",
        "object_id",
    ]


def test_telemetry_csv_preserves_nack_detail_and_stage_latency_fields(tmp_path: Path) -> None:
    logs = (
        _entry(
            frame_timestamp_s=0.2,
            trigger_generation_s=0.2,
            lane=2,
            decision="reject",
            prediction_label="reject",
            rejection_reason="classified_reject",
            protocol_round_trip_ms=5.0,
            ack_code=AckCode.NACK_SAFE,
            trigger_timestamp_s=0.2,
            trigger_mm=304.6,
            lane_index=2,
            belt_speed_mm_s=300.0,
            queue_depth=1,
            scheduler_state="ACTIVE",
            mode="SAFE",
            ingest_latency_ms=0.1,
            decision_latency_ms=0.2,
            schedule_latency_ms=0.3,
            transport_latency_ms=5.0,
            cycle_latency_ms=5.7,
            nack_code=5,
            nack_detail="SAFE",
        ),
    )
    scenarios = (
        BenchScenario("fault", max_avg_rtt_ms=20.0, max_peak_rtt_ms=20.0, require_safe_transition=True, require_recovery=False),
    )
    evaluation = evaluate_logs(logs, scenarios)

    artifact_dir = write_artifacts(logs, evaluation, tmp_path, include_text_report=False)
    rows = (artifact_dir / "telemetry.csv").read_text(encoding="utf-8").splitlines()
    header = rows[0].split(",")
    values = rows[1].split(",")

    assert "ingest_latency_ms" in header
    assert "transport_latency_ms" in header
    assert "nack_code" in header
    assert "nack_detail" in header

    index_nack_detail = header.index("nack_detail")
    assert values[index_nack_detail] == "SAFE"
