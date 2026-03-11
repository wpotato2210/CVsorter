from __future__ import annotations

from unittest.mock import patch

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


class _AckTransportStub:
    def send(self, _command):
        class _Response:
            queue_depth = 0
            scheduler_state = "IDLE"
            mode = "AUTO"
            queue_cleared = False
            round_trip_ms = 0.5
            ack_code = AckCode.ACK
            nack_code = None
            nack_detail = None

        return _Response()


def test_phase2_task15_frame_staleness_above_boundary_forces_safe() -> None:
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    max_frame_staleness_ms = 20.0
    runner = BenchRunner(
        pipeline=_PipelineStub(),
        transport=_AckTransportStub(),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(max_frame_staleness_ms=max_frame_staleness_ms),
    )

    with patch("coloursorter.bench.runner.time.perf_counter") as perf_counter:
        perf_counter.side_effect = [
            100.032,
            100.032,
            100.04,
            100.04,
            100.041,
            100.041,
            100.045,
            100.05,
            100.055,
        ]
        log = runner.run_cycle(
            1,
            1.0,
            20,
            20,
            [detection],
            previous_timestamp_s=0.9,
            captured_monotonic_s=100.01,
        )[0]

    assert log.transport_sent is False
    assert log.over_budget is True
    assert log.fault_event == "FRAME_STALENESS_EXCEEDED"
    assert log.ack_code == AckCode.NACK_SAFE
    assert log.actuator_command_issued is False
