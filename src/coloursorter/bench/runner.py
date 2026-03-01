from __future__ import annotations

from dataclasses import dataclass

from coloursorter.deploy import PipelineRunner
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
    ) -> None:
        self._pipeline = pipeline
        self._transport = transport
        self._encoder = encoder

    def run_cycle(
        self,
        frame_id: int,
        timestamp_s: float,
        image_height_px: int,
        image_width_px: int,
        detections: list[ObjectDetection],
        previous_timestamp_s: float,
    ) -> tuple[BenchLogEntry, ...]:
        frame = FrameMetadata(
            frame_id=frame_id,
            timestamp_s=timestamp_s,
            image_height_px=image_height_px,
            image_width_px=image_width_px,
        )
        pulses = self._encoder.pulses_between(previous_timestamp_s, timestamp_s)
        trigger_generation_s = timestamp_s if pulses > 0 else previous_timestamp_s
        pipeline_result = self._pipeline.run(frame=frame, detections=detections)

        logs: list[BenchLogEntry] = []
        for decision, command in zip(pipeline_result.decisions, pipeline_result.schedule_commands):
            response = self._transport.send(command)
            logs.append(
                BenchLogEntry(
                    frame_timestamp_s=timestamp_s,
                    trigger_generation_s=trigger_generation_s,
                    trigger_timestamp_s=trigger_generation_s,
                    trigger_mm=command.position_mm,
                    lane=decision.lane,
                    lane_index=decision.lane,
                    decision=decision.classification,
                    rejection_reason=decision.rejection_reason,
                    belt_speed_mm_s=self._encoder.belt_speed_mm_per_s,
                    queue_depth=response.queue_depth,
                    scheduler_state=response.scheduler_state,
                    mode=response.mode,
                    protocol_round_trip_ms=response.round_trip_ms,
                    ack_code=response.ack_code,
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
