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
