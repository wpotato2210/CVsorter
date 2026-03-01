from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import csv
import json

from .runner import BenchRunner
from .scenarios import BenchScenario, ScenarioResult
from .types import AckCode, BenchLogEntry


@dataclass(frozen=True)
class BenchEvaluation:
    scenarios: tuple[ScenarioResult, ...]
    summary: dict[str, float | int | bool]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.scenarios)


def evaluate_logs(logs: tuple[BenchLogEntry, ...], scenarios: tuple[BenchScenario, ...]) -> BenchEvaluation:
    bench_summary = BenchRunner.summarize(logs)
    results = tuple(scenario.evaluate(bench_summary) for scenario in scenarios)
    summary = {
        "avg_round_trip_ms": bench_summary.avg_round_trip_ms,
        "max_round_trip_ms": bench_summary.max_round_trip_ms,
        "safe_transitions": bench_summary.safe_transitions,
        "watchdog_transitions": bench_summary.watchdog_transitions,
        "recovered_from_safe": bench_summary.recovered_from_safe,
    }
    return BenchEvaluation(scenarios=results, summary=summary)


def write_artifacts(
    logs: tuple[BenchLogEntry, ...],
    evaluation: BenchEvaluation,
    output_root: str | Path,
    include_text_report: bool,
) -> Path:
    artifact_dir = Path(output_root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir.mkdir(parents=True, exist_ok=False)

    summary_path = artifact_dir / "summary.json"
    telemetry_path = artifact_dir / "telemetry.csv"

    summary_payload = {
        "passed": evaluation.passed,
        "metrics": evaluation.summary,
        "scenarios": [
            {
                "name": result.name,
                "passed": result.passed,
                "detail": result.detail,
            }
            for result in evaluation.scenarios
        ],
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    with telemetry_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
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
                "decision",
                "protocol_round_trip_ms",
                "ingest_latency_ms",
                "decision_latency_ms",
                "schedule_latency_ms",
                "transport_latency_ms",
                "cycle_latency_ms",
                "ack_code",
                "nack_code",
                "nack_detail",
            ]
        )
        for entry in logs:
            ack_code = entry.ack_code.value if isinstance(entry.ack_code, AckCode) else str(entry.ack_code)
            writer.writerow(
                [
                    f"{entry.frame_timestamp_s:.6f}",
                    f"{entry.trigger_generation_s:.6f}",
                    f"{entry.trigger_timestamp_s:.6f}",
                    f"{entry.trigger_mm:.6f}",
                    entry.lane_index,
                    entry.rejection_reason or "",
                    f"{entry.belt_speed_mm_s:.6f}",
                    entry.queue_depth,
                    entry.scheduler_state,
                    entry.mode,
                    entry.decision,
                    f"{entry.protocol_round_trip_ms:.3f}",
                    f"{entry.ingest_latency_ms:.3f}",
                    f"{entry.decision_latency_ms:.3f}",
                    f"{entry.schedule_latency_ms:.3f}",
                    f"{entry.transport_latency_ms:.3f}",
                    f"{entry.cycle_latency_ms:.3f}",
                    ack_code,
                    "" if entry.nack_code is None else entry.nack_code,
                    entry.nack_detail or "",
                ]
            )

    if include_text_report:
        report_lines = [
            f"overall: {'PASS' if evaluation.passed else 'FAIL'}",
            f"avg_rtt_ms: {evaluation.summary['avg_round_trip_ms']:.2f}",
            f"max_rtt_ms: {evaluation.summary['max_round_trip_ms']:.2f}",
        ]
        report_lines.extend(
            f"{result.name}: {'PASS' if result.passed else 'FAIL'} ({result.detail})" for result in evaluation.scenarios
        )
        (artifact_dir / "report.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return artifact_dir
