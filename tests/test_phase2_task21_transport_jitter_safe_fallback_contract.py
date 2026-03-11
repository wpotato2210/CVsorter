from __future__ import annotations

from collections.abc import Sequence

from coloursorter.bench.runner import BenchRunner, BenchSafetyConfig
from coloursorter.bench.types import AckCode
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy.pipeline import PipelineResult, ScheduledDecision
from coloursorter.model import CentroidMM, DecisionPayload, ObjectDetection
from coloursorter.scheduler import build_scheduled_command


class _PipelineStub:
    def __init__(self) -> None:
        decision = DecisionPayload(
            frame_id=1,
            object_id="det-1",
            lane=0,
            centroid_mm=CentroidMM(x_mm=1.0, y_mm=1.0),
            trigger_mm=100.0,
            classification="reject",
            rejection_reason="rule_threshold",
        )
        command = build_scheduled_command(0, 100.0)
        self._result = PipelineResult(
            decisions=(decision,),
            schedule_commands=(command,),
            scheduled_events=(ScheduledDecision("det-1", decision, command),),
        )

    def run(self, frame, detections):
        return self._result


class _AckTransportSequenceStub:
    def __init__(self, round_trip_ms_values: Sequence[float]) -> None:
        self._round_trip_ms_values = list(round_trip_ms_values)
        self._index = 0

    def send(self, _command):
        round_trip_ms = self._round_trip_ms_values[min(self._index, len(self._round_trip_ms_values) - 1)]
        self._index += 1

        class _Response:
            queue_depth = 0
            scheduler_state = "IDLE"
            mode = "AUTO"
            queue_cleared = False
            ack_code = AckCode.ACK
            nack_code = None
            nack_detail = None

        response = _Response()
        response.round_trip_ms = round_trip_ms
        return response


def test_phase2_task21_transport_jitter_critical_is_telemetry_only_contract() -> None:
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    runner = BenchRunner(
        pipeline=_PipelineStub(),
        transport=_AckTransportSequenceStub([1.0, 8.0]),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(jitter_warn_ms=5.0, jitter_critical_ms=7.0),
    )

    runner.run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)
    critical_log = runner.run_cycle(2, 1.1, 20, 20, [detection], previous_timestamp_s=1.0)[0]

    assert critical_log.rtt_jitter_ms == 7.0
    assert critical_log.jitter_warn is True
    assert critical_log.jitter_critical is True

    assert critical_log.fault_event == ""
    assert critical_log.ack_code == AckCode.ACK
    assert critical_log.scheduler_state == "IDLE"
    assert critical_log.queue_cleared is False
    assert critical_log.nack_detail is None
    assert critical_log.transport_sent is True
    assert critical_log.actuator_command_issued is True
