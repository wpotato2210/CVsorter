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
    round_trips = sorted(log.protocol_round_trip_ms for log in logs)
    p50 = _percentile(round_trips, 0.50)
    p95 = _percentile(round_trips, 0.95)
    p99 = _percentile(round_trips, 0.99)
    max_jitter = max((log.rtt_jitter_ms for log in logs), default=0.0)
    summary = {
        "avg_round_trip_ms": bench_summary.avg_round_trip_ms,
        "max_round_trip_ms": bench_summary.max_round_trip_ms,
        "p50_round_trip_ms": p50,
        "p95_round_trip_ms": p95,
        "p99_round_trip_ms": p99,
        "max_jitter_ms": max_jitter,
        "jitter_warn_alarm": any(log.jitter_warn for log in logs),
        "jitter_critical_alarm": any(log.jitter_critical for log in logs),
        "safe_transitions": bench_summary.safe_transitions,
        "watchdog_transitions": bench_summary.watchdog_transitions,
        "recovered_from_safe": bench_summary.recovered_from_safe,
        "reject_reliability": bench_summary.reject_reliability,
        "missed_window_count": bench_summary.missed_window_count,
        "hard_gate_pass": (
            bench_summary.reject_reliability >= 0.99
            and bench_summary.max_jitter_ms <= 10.0
            and bench_summary.missed_window_count == 0
        ),
    }
    return BenchEvaluation(scenarios=results, summary=summary)


def _percentile(sorted_values: list[float], quantile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = (len(sorted_values) - 1) * quantile
    low = int(index)
    high = min(low + 1, len(sorted_values) - 1)
    weight = index - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def write_artifacts(
    logs: tuple[BenchLogEntry, ...],
    evaluation: BenchEvaluation,
    output_root: str | Path,
    include_text_report: bool,
    config_snapshot: dict[str, object] | None = None,
    audit_trail: tuple[dict[str, object], ...] = (),
) -> Path:
    artifact_dir = Path(output_root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir.mkdir(parents=True, exist_ok=False)

    summary_path = artifact_dir / "summary.json"
    telemetry_path = artifact_dir / "telemetry.csv"
    events_path = artifact_dir / "events.jsonl"
    audit_path = artifact_dir / "audit_trail.jsonl"

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
                "protocol_frame": entry.protocol_frame,
                "transport_sent": entry.transport_sent,
                "transport_acknowledged": entry.transport_acknowledged,
                "scheduler_window_missed": entry.scheduler_window_missed,
                "transport_nack_detail": entry.nack_detail or "",
                "queue_depth": entry.queue_depth,
                "ingest_latency_ms": entry.ingest_latency_ms,
                "decision_latency_ms": entry.decision_latency_ms,
                "detect_latency_ms": entry.detect_latency_ms,
                "schedule_latency_ms": entry.schedule_latency_ms,
                "transport_latency_ms": entry.transport_latency_ms,
                "cycle_latency_ms": entry.cycle_latency_ms,
                "queue_age_ms": entry.queue_age_ms,
                "frame_staleness_ms": entry.frame_staleness_ms,
                "total_budget_ms": entry.total_budget_ms,
                "over_budget": entry.over_budget,
                "fault_event": entry.fault_event,
                "timebase_reference": entry.timebase_reference,
                "trigger_reference_s": entry.trigger_reference_s,
                "rtt_jitter_ms": entry.rtt_jitter_ms,
                "jitter_warn": entry.jitter_warn,
                "jitter_critical": entry.jitter_critical,
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
                "protocol_frame",
                "transport_sent",
                "transport_acknowledged",
                "scheduler_window_missed",
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
                "detect_latency_ms",
                "schedule_latency_ms",
                "transport_latency_ms",
                "cycle_latency_ms",
                "queue_age_ms",
                "frame_staleness_ms",
                "total_budget_ms",
                "over_budget",
                "fault_event",
                "timebase_reference",
                "trigger_reference_s",
                "rtt_jitter_ms",
                "jitter_warn",
                "jitter_critical",
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
                    entry.protocol_frame,
                    str(entry.transport_sent).lower(),
                    str(entry.transport_acknowledged).lower(),
                    str(entry.scheduler_window_missed).lower(),
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
                    f"{entry.detect_latency_ms:.3f}",
                    f"{entry.schedule_latency_ms:.3f}",
                    f"{entry.transport_latency_ms:.3f}",
                    f"{entry.cycle_latency_ms:.3f}",
                    f"{entry.queue_age_ms:.3f}",
                    f"{entry.frame_staleness_ms:.3f}",
                    f"{entry.total_budget_ms:.3f}",
                    str(entry.over_budget).lower(),
                    entry.fault_event,
                    entry.timebase_reference,
                    f"{entry.trigger_reference_s:.6f}",
                    f"{entry.rtt_jitter_ms:.3f}",
                    str(entry.jitter_warn).lower(),
                    str(entry.jitter_critical).lower(),
                    ack_code,
                    "" if entry.nack_code is None else entry.nack_code,
                    entry.nack_detail or "",
                ]
            )

    if config_snapshot is not None:
        (artifact_dir / "config_snapshot.json").write_text(json.dumps(config_snapshot, indent=2), encoding="utf-8")

    with audit_path.open("w", encoding="utf-8") as handle:
        for event in audit_trail:
            handle.write(json.dumps(event) + "\n")

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
