from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import time

from coloursorter.deploy import ActuatorTimingCalibrator, PipelineRunner
from coloursorter.ingest import DeterministicDropPolicy, IngestBoundary
from coloursorter.model import FrameMetadata, ObjectDetection

from .transport import McuTransport
from .scenarios import BenchSummary
from .types import AckCode, BenchLogEntry
from .virtual_encoder import VirtualEncoder


@dataclass(frozen=True)
class BenchRunResult:
    logs: tuple[BenchLogEntry, ...]
    summary: BenchSummary


class BenchRunner:
    def __init__(
        self,
        pipeline: PipelineRunner,
        transport: McuTransport,
        encoder: VirtualEncoder,
        calibrator: ActuatorTimingCalibrator | None = None,
        ingest_boundary: IngestBoundary | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._transport = transport
        self._encoder = encoder
        self._calibrator = calibrator or ActuatorTimingCalibrator()
        self._latency_samples_ms: list[float] = []
        self._ingest_boundary = ingest_boundary or IngestBoundary(
            contract_path=Path(__file__).resolve().parents[3] / "contracts" / "frame_schema.json",
            capacity=1,
            drop_policy=DeterministicDropPolicy.DROP_OLDEST,
        )

    def process_ingest_payload(self, payload: dict[str, object]) -> tuple[BenchLogEntry, ...]:
        self._ingest_boundary.submit(payload)
        cycle_input = self._ingest_boundary.next_cycle_input()
        if cycle_input is None:
            return ()
        return self.run_cycle(
            frame_id=cycle_input.frame.frame_id,
            timestamp_s=cycle_input.frame.timestamp_s,
            image_height_px=cycle_input.frame.image_height_px,
            image_width_px=cycle_input.frame.image_width_px,
            detections=list(cycle_input.detections),
            previous_timestamp_s=cycle_input.previous_timestamp_s,
            run_id=cycle_input.run_id,
            test_batch_id=cycle_input.test_batch_id,
            frame_snapshot_path=cycle_input.frame_snapshot_path,
            ground_truth_by_object_id=cycle_input.ground_truth_by_object_id,
        )

    def run_cycle(
        self,
        frame_id: int,
        timestamp_s: float,
        image_height_px: int,
        image_width_px: int,
        detections: list[ObjectDetection],
        previous_timestamp_s: float,
        run_id: str = "default-run",
        test_batch_id: str = "default-batch",
        frame_snapshot_path: str = "",
        ground_truth_by_object_id: dict[str, str] | None = None,
    ) -> tuple[BenchLogEntry, ...]:
        cycle_started = time.perf_counter()
        ingest_started = cycle_started
        frame = FrameMetadata(
            frame_id=frame_id,
            timestamp_s=timestamp_s,
            image_height_px=image_height_px,
            image_width_px=image_width_px,
        )
        self._encoder.pulses_between(previous_timestamp_s, timestamp_s)
        trigger_generation_s = self._encoder.resolve_trigger_generation_timestamp(previous_timestamp_s)
        ingest_latency_ms = (time.perf_counter() - ingest_started) * 1000.0

        decision_started = time.perf_counter()
        pipeline_result = self._pipeline.run(frame=frame, detections=detections)
        decision_latency_ms = (time.perf_counter() - decision_started) * 1000.0

        schedule_started = time.perf_counter()
        schedule_latency_ms = (time.perf_counter() - schedule_started) * 1000.0
        self._latency_samples_ms.append(decision_latency_ms + schedule_latency_ms)
        calibration = self._calibrator.calibrate(self._latency_samples_ms[-100:], self._encoder.belt_speed_mm_per_s)

        logs: list[BenchLogEntry] = []
        decision_by_object_id = {decision.object_id: decision for decision in pipeline_result.decisions}
        command_by_object_id = {event.object_id: event.command for event in pipeline_result.scheduled_events}

        for detection in detections:
            decision = decision_by_object_id[detection.object_id]
            command = command_by_object_id.get(detection.object_id)
            if command is not None:
                command_position_mm = max(0.0, command.position_mm - calibration.offset_mm)
                actuator_command_payload = f"lane={command.lane};position_mm={command_position_mm:.3f}"
            else:
                command_position_mm = 0.0
                actuator_command_payload = ""

            belt_speed_mm_s = self._encoder.belt_speed_mm_per_s
            decision_schedule_time_s = (decision_latency_ms + schedule_latency_ms) / 1000.0
            projected_trigger_timestamp_s = self._encoder.project_trigger_timestamp(
                trigger_generation_s=trigger_generation_s,
                trigger_distance_mm=command_position_mm,
                schedule_time_s=decision_schedule_time_s,
            )

            if command is not None:
                transport_started = time.perf_counter()
                response = self._transport.send(command)
                transport_latency_ms = (time.perf_counter() - transport_started) * 1000.0
                actuator_issued = True
            else:
                transport_latency_ms = 0.0
                actuator_issued = False
                response = type("_Resp", (), {
                    "queue_depth": 0,
                    "scheduler_state": "SKIPPED",
                    "mode": "AUTO",
                    "queue_cleared": False,
                    "round_trip_ms": 0.0,
                    "ack_code": AckCode.ACK,
                    "nack_code": None,
                    "nack_detail": None,
                })()

            cycle_latency_ms = (time.perf_counter() - cycle_started) * 1000.0
            logs.append(
                BenchLogEntry(
                    run_id=run_id,
                    test_batch_id=test_batch_id,
                    event_timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    frame_timestamp_s=timestamp_s,
                    frame_id=frame_id,
                    object_id=detection.object_id,
                    trigger_generation_s=trigger_generation_s,
                    trigger_timestamp_s=projected_trigger_timestamp_s,
                    trigger_mm=command_position_mm,
                    lane=decision.lane,
                    lane_index=decision.lane,
                    decision=decision.classification,
                    prediction_label=detection.classification,
                    confidence=detection.infection_score,
                    rejection_reason=decision.rejection_reason,
                    decision_reason=decision.rejection_reason or "accepted",
                    belt_speed_mm_s=belt_speed_mm_s,
                    queue_depth=response.queue_depth,
                    scheduler_state=response.scheduler_state,
                    mode=response.mode,
                    queue_cleared=response.queue_cleared,
                    protocol_round_trip_ms=response.round_trip_ms,
                    ack_code=response.ack_code,
                    ingest_latency_ms=ingest_latency_ms,
                    decision_latency_ms=decision_latency_ms,
                    schedule_latency_ms=schedule_latency_ms,
                    transport_latency_ms=transport_latency_ms,
                    cycle_latency_ms=cycle_latency_ms,
                    nack_code=response.nack_code,
                    nack_detail=response.nack_detail,
                    actuator_command_issued=actuator_issued,
                    actuator_command_payload=actuator_command_payload,
                    frame_snapshot_path=frame_snapshot_path,
                    ground_truth_label=(ground_truth_by_object_id or {}).get(detection.object_id, ""),
                )
            )
        return tuple(logs)

    @staticmethod
    def summarize(logs: tuple[BenchLogEntry, ...]) -> BenchSummary:
        if not logs:
            return BenchSummary(
                avg_round_trip_ms=0.0,
                max_round_trip_ms=0.0,
                safe_transitions=0,
                watchdog_transitions=0,
                recovered_from_safe=False,
            )

        round_trips = [log.protocol_round_trip_ms for log in logs]
        ack_codes = [log.ack_code for log in logs]
        safe_indices = [i for i, code in enumerate(ack_codes) if code == AckCode.NACK_SAFE]
        recovered = bool(safe_indices and ack_codes[-1] == AckCode.ACK and max(safe_indices) < len(ack_codes) - 1)
        return BenchSummary(
            avg_round_trip_ms=sum(round_trips) / len(round_trips),
            max_round_trip_ms=max(round_trips),
            safe_transitions=len(safe_indices),
            watchdog_transitions=sum(1 for code in ack_codes if code == AckCode.NACK_WATCHDOG),
            recovered_from_safe=recovered,
        )
