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
    config_snapshot: dict[str, object] | None = None,
) -> Path:
    artifact_dir = Path(output_root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir.mkdir(parents=True, exist_ok=False)

    summary_path = artifact_dir / "summary.json"
    telemetry_path = artifact_dir / "telemetry.csv"
    events_path = artifact_dir / "events.jsonl"

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

    with events_path.open("w", encoding="utf-8") as handle:
        for entry in logs:
            ack_code = entry.ack_code.value if isinstance(entry.ack_code, AckCode) else str(entry.ack_code)
            payload = {
                "run_id": entry.run_id,
                "test_batch_id": entry.test_batch_id,
                "event_timestamp_utc": entry.event_timestamp_utc,
                "frame_id": entry.frame_id,
                "object_id": entry.object_id,
                "prediction_label": entry.prediction_label,
                "confidence": entry.confidence,
                "decision_label": entry.decision,
                "decision_reason": entry.decision_reason,
                "lane_index": entry.lane_index,
                "trigger_mm": entry.trigger_mm,
                "trigger_timestamp_s": entry.trigger_timestamp_s,
                "actuator_command_issued": entry.actuator_command_issued,
                "actuator_command_payload": entry.actuator_command_payload,
                "command_source": entry.command_source,
                "transport_ack_code": ack_code,
                "transport_nack_code": "" if entry.nack_code is None else entry.nack_code,
                "transport_nack_detail": entry.nack_detail or "",
                "queue_depth": entry.queue_depth,
                "ingest_latency_ms": entry.ingest_latency_ms,
                "decision_latency_ms": entry.decision_latency_ms,
                "schedule_latency_ms": entry.schedule_latency_ms,
                "transport_latency_ms": entry.transport_latency_ms,
                "cycle_latency_ms": entry.cycle_latency_ms,
                "frame_snapshot_path": entry.frame_snapshot_path,
                "ground_truth_label": entry.ground_truth_label,
            }
            handle.write(json.dumps(payload) + "\n")

    with telemetry_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "run_id",
                "test_batch_id",
                "event_timestamp_utc",
                "frame_timestamp",
                "frame_id",
                "object_id",
                "trigger_generation_timestamp",
                "trigger_timestamp",
                "trigger_mm",
                "lane_index",
                "rejection_reason",
                "decision_reason",
                "prediction_label",
                "confidence",
                "actuator_command_issued",
                "actuator_command_payload",
                "command_source",
                "frame_snapshot_path",
                "ground_truth_label",
                "belt_speed_mm_s",
                "queue_depth",
                "scheduler_state",
                "mode",
                "queue_cleared",
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
                    entry.run_id,
                    entry.test_batch_id,
                    entry.event_timestamp_utc,
                    f"{entry.frame_timestamp_s:.6f}",
                    entry.frame_id,
                    entry.object_id,
                    f"{entry.trigger_generation_s:.6f}",
                    f"{entry.trigger_timestamp_s:.6f}",
                    f"{entry.trigger_mm:.6f}",
                    entry.lane_index,
                    entry.rejection_reason or "",
                    entry.decision_reason,
                    entry.prediction_label,
                    f"{entry.confidence:.3f}",
                    str(entry.actuator_command_issued).lower(),
                    entry.actuator_command_payload,
                    entry.command_source,
                    entry.frame_snapshot_path,
                    entry.ground_truth_label,
                    f"{entry.belt_speed_mm_s:.6f}",
                    entry.queue_depth,
                    entry.scheduler_state,
                    entry.mode,
                    str(entry.queue_cleared).lower(),
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

    if config_snapshot is not None:
        (artifact_dir / "config_snapshot.json").write_text(json.dumps(config_snapshot, indent=2), encoding="utf-8")

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
