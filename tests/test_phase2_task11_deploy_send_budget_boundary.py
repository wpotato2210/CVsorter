from __future__ import annotations

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


class _ExactBudgetTransportStub:
    def __init__(self, round_trip_ms: float) -> None:
        self._round_trip_ms = round_trip_ms

    def send(self, _command):
        class _Response:
            queue_depth = 0
            scheduler_state = "IDLE"
            mode = "AUTO"
            queue_cleared = False
            ack_code = AckCode.ACK
            nack_code = None
            nack_detail = None

            def __init__(self, round_trip_ms: float) -> None:
                self.round_trip_ms = round_trip_ms

        return _Response(self._round_trip_ms)


def test_phase2_task11_send_budget_allows_equal_boundary_without_safe_transition() -> None:
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    send_budget_ms = 1.0
    runner = BenchRunner(
        pipeline=_PipelineStub(),
        transport=_ExactBudgetTransportStub(round_trip_ms=send_budget_ms),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(send_budget_ms=send_budget_ms),
    )

    log = runner.run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)[0]

    assert log.transport_sent is True
    assert log.over_budget is False
    assert log.fault_event == ""
    assert log.ack_code == AckCode.ACK
    assert log.actuator_command_issued is True
