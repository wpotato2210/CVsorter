from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import time

from coloursorter.deploy import ActuatorTimingCalibrator, PipelineRunner
from coloursorter.ingest import DeterministicDropPolicy, IngestBoundary
from coloursorter.model import FrameMetadata, ObjectDetection
from coloursorter.scheduler import build_scheduled_command

from .transport import McuTransport
from .scenarios import BenchSummary
from .types import AckCode, BenchLogEntry
from .virtual_encoder import VirtualEncoder


@dataclass(frozen=True)
class BenchRunResult:
    logs: tuple[BenchLogEntry, ...]
    summary: BenchSummary


@dataclass(frozen=True)
class BenchSafetyConfig:
    ingest_budget_ms: float = 100.0
    detect_budget_ms: float = 100.0
    decide_budget_ms: float = 100.0
    send_budget_ms: float = 100.0
    total_budget_ms: float = 400.0
    max_queue_age_ms: float = 20.0
    max_frame_staleness_ms: float = 50.0
    timebase_strategy: str = "encoder_epoch"
    host_to_mcu_offset_ms: float = 0.0
    jitter_warn_ms: float = 5.0
    jitter_critical_ms: float = 10.0
    detect_timeout_fallback: str = "SAFE"


class BenchRunner:
    def __init__(
        self,
        pipeline: PipelineRunner,
        transport: McuTransport,
        encoder: VirtualEncoder,
        calibrator: ActuatorTimingCalibrator | None = None,
        ingest_boundary: IngestBoundary | None = None,
        safety: BenchSafetyConfig | None = None,
        provider_version: str = "",
        model_version: str = "",
        active_config_hash: str = "",
    ) -> None:
        self._pipeline = pipeline
        self._transport = transport
        self._encoder = encoder
        self._calibrator = calibrator or ActuatorTimingCalibrator()
        self._latency_samples_ms: list[float] = []
        self._issued_command_keys: set[tuple[int, str]] = set()
        self._ingest_boundary = ingest_boundary or IngestBoundary(
            contract_path=Path(__file__).resolve().parents[3] / "contracts" / "frame_schema.json",
            capacity=1,
            drop_policy=DeterministicDropPolicy.DROP_OLDEST,
        )
        self._safety = safety or BenchSafetyConfig()
        self._last_round_trip_ms: float | None = None
        self._provider_version = provider_version
        self._model_version = model_version
        self._active_config_hash = active_config_hash

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
            enqueued_monotonic_s=cycle_input.enqueued_monotonic_s,
            captured_monotonic_s=cycle_input.captured_monotonic_s,
            detect_latency_ms=cycle_input.detect_latency_ms,
            detection_provider_version=cycle_input.detection_provider_version,
            detection_model_version=cycle_input.detection_model_version,
            active_config_hash=cycle_input.active_config_hash,
            preprocess_metrics=cycle_input.preprocess_metrics,
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
        enqueued_monotonic_s: float = 0.0,
        captured_monotonic_s: float = 0.0,
        detect_latency_ms: float = 0.0,
        detection_provider_version: str = "",
        detection_model_version: str = "",
        active_config_hash: str = "",
        preprocess_metrics: dict[str, float | bool] | None = None,
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

        queue_age_ms = max(0.0, (cycle_started - enqueued_monotonic_s) * 1000.0) if enqueued_monotonic_s > 0.0 else 0.0
        frame_staleness_ms = max(0.0, (cycle_started - captured_monotonic_s) * 1000.0) if captured_monotonic_s > 0.0 else 0.0

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

        stage_over_budget = {
            "ingest": ingest_latency_ms > self._safety.ingest_budget_ms,
            "detect": detect_latency_ms > self._safety.detect_budget_ms,
            "decide": decision_latency_ms > self._safety.decide_budget_ms,
        }

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
            if self._safety.timebase_strategy == "host_to_mcu_offset":
                projected_trigger_timestamp_s += self._safety.host_to_mcu_offset_ms / 1000.0

            command_source = ""
            fault_event = ""
            if command is not None:
                command_key = (frame_id, detection.object_id)
                if command_key in self._issued_command_keys:
                    command = None
                    command_position_mm = 0.0
                    actuator_command_payload = ""
                else:
                    self._issued_command_keys.add(command_key)

            if queue_age_ms > self._safety.max_queue_age_ms:
                fault_event = "QUEUE_AGE_EXCEEDED"
                command = None
            elif frame_staleness_ms > self._safety.max_frame_staleness_ms:
                fault_event = "FRAME_STALENESS_EXCEEDED"
                command = None

            cycle_no_send_ms = ingest_latency_ms + detect_latency_ms + decision_latency_ms + schedule_latency_ms
            if cycle_no_send_ms > self._safety.total_budget_ms or any(stage_over_budget.values()):
                fault_event = fault_event or "CYCLE_BUDGET_EXCEEDED"
                detect_timeout = stage_over_budget["detect"]
                fallback_mode = self._safety.detect_timeout_fallback.upper()
                if detect_timeout and fallback_mode == "REJECT" and decision.lane >= 0:
                    if command is None:
                        command = build_scheduled_command(decision.lane, max(0.0, decision.trigger_mm))
                        command_position_mm = max(0.0, command.position_mm - calibration.offset_mm)
                        actuator_command_payload = f"lane={command.lane};position_mm={command.position_mm:.2f}"
                    fault_event = "DETECT_TIMEOUT_REJECT_MODE"
                else:
                    command = None

            protocol_frame = ""
            transport_sent = False
            transport_acknowledged = False
            scheduler_window_missed = bool(fault_event in {"QUEUE_AGE_EXCEEDED", "FRAME_STALENESS_EXCEEDED"})
            if command is not None:
                protocol_frame = f"SCHED|{command.lane}|{command.position_mm:.3f}"
                transport_started = time.perf_counter()
                response = self._transport.send(command)
                transport_latency_ms = (time.perf_counter() - transport_started) * 1000.0
                transport_sent = True
                if transport_latency_ms > self._safety.send_budget_ms:
                    fault_event = "SEND_BUDGET_EXCEEDED"
                    response = type("_Resp", (), {
                        "queue_depth": 0,
                        "scheduler_state": "SAFE",
                        "mode": "AUTO",
                        "queue_cleared": True,
                        "round_trip_ms": 0.0,
                        "ack_code": AckCode.NACK_SAFE,
                        "nack_code": None,
                        "nack_detail": fault_event,
                    })()
                    actuator_issued = False
                    command_source = ""
                else:
                    actuator_issued = True
                    command_source = "auto_pipeline"
                    transport_acknowledged = response.ack_code == AckCode.ACK
            else:
                transport_latency_ms = 0.0
                actuator_issued = False
                response = type("_Resp", (), {
                    "queue_depth": 0,
                    "scheduler_state": "SAFE" if fault_event else "SKIPPED",
                    "mode": "AUTO",
                    "queue_cleared": bool(fault_event),
                    "round_trip_ms": 0.0,
                    "ack_code": AckCode.NACK_SAFE if fault_event else AckCode.ACK,
                    "nack_code": None,
                    "nack_detail": fault_event or None,
                })()

            if response.mode == "AUTO":
                active_sources = {source for source in (command_source,) if source in {"manual_test", "auto_pipeline"}}
                assert len(active_sources) <= 1, "AUTO mode must have a single command source"
                if command_source == "manual_test":
                    raise AssertionError("AUTO mode cannot emit manual_test commands")

            cycle_latency_ms = (time.perf_counter() - cycle_started) * 1000.0
            total_budget_ms = ingest_latency_ms + detect_latency_ms + decision_latency_ms + transport_latency_ms
            over_budget = bool(fault_event)
            rtt_jitter_ms = (
                abs(response.round_trip_ms - self._last_round_trip_ms)
                if self._last_round_trip_ms is not None
                else 0.0
            )
            self._last_round_trip_ms = response.round_trip_ms
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
                    record_type="actuation_cycle",
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
                    detect_latency_ms=detect_latency_ms,
                    decision_latency_ms=decision_latency_ms,
                    schedule_latency_ms=schedule_latency_ms,
                    transport_latency_ms=transport_latency_ms,
                    cycle_latency_ms=cycle_latency_ms,
                    queue_age_ms=queue_age_ms,
                    frame_staleness_ms=frame_staleness_ms,
                    total_budget_ms=total_budget_ms,
                    over_budget=over_budget,
                    fault_event=fault_event,
                    timebase_reference=self._safety.timebase_strategy,
                    trigger_reference_s=trigger_generation_s,
                    rtt_jitter_ms=rtt_jitter_ms,
                    jitter_warn=rtt_jitter_ms >= self._safety.jitter_warn_ms,
                    jitter_critical=rtt_jitter_ms >= self._safety.jitter_critical_ms,
                    nack_code=response.nack_code,
                    nack_detail=response.nack_detail,
                    actuator_command_issued=actuator_issued,
                    actuator_command_payload=actuator_command_payload,
                    command_source=command_source,
                    frame_snapshot_path=frame_snapshot_path,
                    ground_truth_label=(ground_truth_by_object_id or {}).get(detection.object_id, ""),
                    detection_provider_version=detection_provider_version or self._provider_version,
                    detection_model_version=detection_model_version or self._model_version,
                    active_config_hash=active_config_hash or self._active_config_hash,
                    preprocess_valid=bool((preprocess_metrics or {}).get("preprocess_valid", True)),
                    preprocess_luma_before=float((preprocess_metrics or {}).get("luma_before", 0.0)),
                    preprocess_luma_after=float((preprocess_metrics or {}).get("luma_after", 0.0)),
                    preprocess_exposure_gain=float((preprocess_metrics or {}).get("exposure_gain", 1.0)),
                    preprocess_wb_gain_b=float((preprocess_metrics or {}).get("wb_gain_b", 1.0)),
                    preprocess_wb_gain_g=float((preprocess_metrics or {}).get("wb_gain_g", 1.0)),
                    preprocess_wb_gain_r=float((preprocess_metrics or {}).get("wb_gain_r", 1.0)),
                    preprocess_clipped_ratio=float((preprocess_metrics or {}).get("clipped_ratio", 0.0)),
                    protocol_frame=protocol_frame,
                    transport_sent=transport_sent,
                    transport_acknowledged=transport_acknowledged,
                    scheduler_window_missed=scheduler_window_missed,
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
                reject_reliability=1.0,
                max_jitter_ms=0.0,
                missed_window_count=0,
            )

        round_trips = [log.protocol_round_trip_ms for log in logs]
        ack_codes = [log.ack_code for log in logs]
        safe_indices = [i for i, code in enumerate(ack_codes) if code == AckCode.NACK_SAFE]
        recovered = bool(safe_indices and ack_codes[-1] == AckCode.ACK and max(safe_indices) < len(ack_codes) - 1)
        expected_rejects = [
            log for log in logs
            if log.decision == "reject" and not log.scheduler_window_missed
        ]
        successful_rejects = [
            log for log in expected_rejects
            if log.transport_sent and log.transport_acknowledged and log.actuator_command_issued
        ]
        reject_reliability = (
            len(successful_rejects) / len(expected_rejects)
            if expected_rejects
            else 1.0
        )
        return BenchSummary(
            avg_round_trip_ms=sum(round_trips) / len(round_trips),
            max_round_trip_ms=max(round_trips),
            safe_transitions=len(safe_indices),
            watchdog_transitions=sum(1 for code in ack_codes if code == AckCode.NACK_WATCHDOG),
            recovered_from_safe=recovered,
            reject_reliability=reject_reliability,
            max_jitter_ms=max((log.rtt_jitter_ms for log in logs), default=0.0),
            missed_window_count=sum(1 for log in logs if log.scheduler_window_missed),
        )
