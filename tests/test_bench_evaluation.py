from __future__ import annotations

import json
from pathlib import Path

from coloursorter.bench import AckCode, BenchLogEntry, BenchScenario
from coloursorter.bench.evaluation import evaluate_logs, write_artifacts


def test_evaluate_logs_applies_scenarios() -> None:
    logs = (
        BenchLogEntry(0.0, 0.0, 0, "accept", None, 10.0, AckCode.ACK),
        BenchLogEntry(0.1, 0.1, 0, "accept", None, 12.0, AckCode.ACK),
    )
    scenarios = (
        BenchScenario("tight", max_avg_rtt_ms=11.0, max_peak_rtt_ms=15.0, require_safe_transition=False, require_recovery=False),
    )

    evaluation = evaluate_logs(logs, scenarios)

    assert evaluation.passed
    assert evaluation.summary["avg_round_trip_ms"] == 11.0
    assert evaluation.scenarios[0].name == "tight"


def test_write_artifacts_writes_summary_and_telemetry(tmp_path: Path) -> None:
    logs = (
        BenchLogEntry(0.0, 0.0, 1, "reject", "rule", 6.5, AckCode.NACK_SAFE),
    )
    scenarios = (
        BenchScenario("fault", max_avg_rtt_ms=8.0, max_peak_rtt_ms=10.0, require_safe_transition=True, require_recovery=False),
    )
    evaluation = evaluate_logs(logs, scenarios)

    artifact_dir = write_artifacts(logs, evaluation, tmp_path, include_text_report=True)

    summary_payload = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    telemetry_lines = (artifact_dir / "telemetry.csv").read_text(encoding="utf-8").strip().splitlines()

    assert summary_payload["passed"] is True
    assert summary_payload["scenarios"][0]["name"] == "fault"
    assert len(telemetry_lines) == 2
    assert (artifact_dir / "report.txt").exists()


def test_telemetry_csv_includes_required_openspec_v3_fields(tmp_path: Path) -> None:
    logs = (
        BenchLogEntry(
            frame_timestamp_s=0.2,
            trigger_generation_s=0.2,
            lane=2,
            decision="reject",
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

    assert header[:10] == [
        "frame_timestamp",
        "trigger_generation_timestamp",
        "trigger_timestamp",
        "trigger_mm",
        "lane_index",
        "rejection_reason",
        "belt_speed_mm_s",
        "queue_depth",
        "scheduler_state",
        "mode",
    ]


def test_telemetry_csv_preserves_nack_detail_and_stage_latency_fields(tmp_path: Path) -> None:
    logs = (
        BenchLogEntry(
            frame_timestamp_s=0.2,
            trigger_generation_s=0.2,
            lane=2,
            decision="reject",
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
