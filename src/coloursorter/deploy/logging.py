from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class CanonicalTimingDiagnostics:
    """Canonical deterministic runtime timing values in milliseconds.

    Sampling point and formulas (all units are ms):
    - frame_timestamp_ms: Capture timestamp of the input frame in host wall-clock epoch.
      Formula: frame timestamp seconds * 1000 at ingest/reporting time.
    - pipeline_latency_ms: End-to-end host processing time before transport.
      Formula: ingest_latency_ms + decision_latency_ms + schedule_latency_ms.
    - trigger_offset_ms: Time from frame timestamp to projected trigger point.
      Formula: projected_trigger_timestamp_s*1000 - frame_timestamp_ms when available;
      fallback: max(0, cycle_latency_ms - pipeline_latency_ms - transport_latency_ms).
    - actuation_delay_ms: Delay between command emission and transport acknowledgement.
      Formula: transport_latency_ms.
    """

    frame_timestamp_ms: float
    pipeline_latency_ms: float
    trigger_offset_ms: float
    actuation_delay_ms: float


def to_canonical_timing_diagnostics(
    *,
    frame_timestamp_ms: float,
    ingest_latency_ms: float,
    decision_latency_ms: float,
    schedule_latency_ms: float,
    transport_latency_ms: float,
    cycle_latency_ms: float,
    trigger_offset_ms: float | None = None,
) -> CanonicalTimingDiagnostics:
    pipeline_latency_ms = ingest_latency_ms + decision_latency_ms + schedule_latency_ms
    resolved_trigger_offset_ms = (
        trigger_offset_ms
        if trigger_offset_ms is not None
        else max(0.0, cycle_latency_ms - pipeline_latency_ms - transport_latency_ms)
    )
    return CanonicalTimingDiagnostics(
        frame_timestamp_ms=frame_timestamp_ms,
        pipeline_latency_ms=pipeline_latency_ms,
        trigger_offset_ms=resolved_trigger_offset_ms,
        actuation_delay_ms=transport_latency_ms,
    )


@dataclass(frozen=True)
class BaselineEvent:
    run_id: str
    test_batch_id: str
    event_timestamp_utc: str
    frame_id: int
    object_id: str
    prediction_label: str
    confidence: float
    decision_label: str
    decision_reason: str
    lane_index: int
    trigger_mm: float
    trigger_timestamp_s: float
    actuator_command_issued: bool
    actuator_command_payload: str
    transport_ack_code: str
    transport_nack_code: str
    transport_nack_detail: str
    queue_depth: int
    ingest_latency_ms: float
    decision_latency_ms: float
    schedule_latency_ms: float
    transport_latency_ms: float
    cycle_latency_ms: float
    frame_timestamp_ms: float
    pipeline_latency_ms: float
    trigger_offset_ms: float
    actuation_delay_ms: float
    frame_snapshot_path: str
    ground_truth_label: str


class BaselineEventLogger:
    def __init__(self, artifact_dir: str | Path) -> None:
        self._artifact_dir = Path(artifact_dir)
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[BaselineEvent] = []

    @staticmethod
    def utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def append(self, event: BaselineEvent) -> None:
        self._events.append(event)

    def dump(self) -> tuple[Path, Path]:
        jsonl_path = self._artifact_dir / "events.jsonl"
        csv_path = self._artifact_dir / "telemetry.csv"

        with jsonl_path.open("w", encoding="utf-8") as handle:
            for event in self._events:
                handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(self._events[0]).keys()) if self._events else list(asdict(BaselineEvent(
                run_id="", test_batch_id="", event_timestamp_utc="", frame_id=0, object_id="", prediction_label="", confidence=0.0,
                decision_label="", decision_reason="", lane_index=-1, trigger_mm=0.0, trigger_timestamp_s=0.0, actuator_command_issued=False,
                actuator_command_payload="", transport_ack_code="", transport_nack_code="", transport_nack_detail="", queue_depth=0,
                ingest_latency_ms=0.0, decision_latency_ms=0.0, schedule_latency_ms=0.0, transport_latency_ms=0.0, cycle_latency_ms=0.0,
                frame_timestamp_ms=0.0, pipeline_latency_ms=0.0, trigger_offset_ms=0.0, actuation_delay_ms=0.0,
                frame_snapshot_path="", ground_truth_label=""
            )).keys()))
            writer.writeheader()
            for event in self._events:
                writer.writerow(asdict(event))

        return jsonl_path, csv_path
