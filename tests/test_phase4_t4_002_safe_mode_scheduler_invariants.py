from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.bench.mock_transport import MockMcuTransport, MockTransportConfig
from coloursorter.bench.runner import BenchRunner
from coloursorter.bench.types import AckCode, FaultState
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy.pipeline import PipelineResult, ScheduledDecision
from coloursorter.model import CentroidMM, DecisionPayload, ObjectDetection
from coloursorter.scheduler import ScheduledCommand, build_scheduled_command

_FIXTURE = Path(__file__).parent / "fixtures" / "scheduler_safe_stress_t4_002.json"


class _RejectingPipelineStub:
    def __init__(self) -> None:
        decision = DecisionPayload(
            frame_id=1,
            object_id="det-safe",
            lane=0,
            centroid_mm=CentroidMM(x_mm=0.0, y_mm=0.0),
            trigger_mm=100.0,
            classification="reject",
            rejection_reason="rule_threshold",
        )
        command = build_scheduled_command(0, 100.0)
        self._result = PipelineResult(
            decisions=(decision,),
            schedule_commands=(command,),
            scheduled_events=(ScheduledDecision("det-safe", decision, command),),
        )

    def run(self, frame, detections):
        return self._result


def _load_commands() -> list[ScheduledCommand]:
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return [build_scheduled_command(item["lane"], item["position_mm"]) for item in payload["commands"]]


def test_t4_002_scheduler_queue_ordering_is_stable_under_stress_fixture() -> None:
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    commands = _load_commands()

    transport = MockMcuTransport(
        config=MockTransportConfig(
            max_queue_depth=fixture["max_queue_depth"],
            base_round_trip_ms=0.4,
            per_item_penalty_ms=0.2,
        )
    )

    for command in commands:
        response = transport.send(command)
        assert response.ack_code == AckCode.ACK

    queued_pairs = [(command.lane, command.position_mm) for command in transport.queue]
    expected_pairs = [(command.lane, command.position_mm) for command in commands]
    assert queued_pairs == expected_pairs


@pytest.mark.xfail(reason="T4-002 invariant gap: BenchRunner marks actuation issued even in SAFE mode response")
def test_t4_002_safe_mode_invariant_no_actuation_when_scheduler_reports_safe() -> None:
    runner = BenchRunner(
        pipeline=_RejectingPipelineStub(),
        transport=MockMcuTransport(
            config=MockTransportConfig(max_queue_depth=4, base_round_trip_ms=0.5, per_item_penalty_ms=0.1),
            fault_state=FaultState.SAFE,
        ),
        encoder=VirtualEncoder(EncoderConfig(pulses_per_rev=2048, mm_per_rev=100.0, belt_speed_mm_per_s=200.0)),
    )

    logs = runner.run_cycle(
        frame_id=1,
        timestamp_s=1.0,
        image_height_px=32,
        image_width_px=32,
        detections=[ObjectDetection("det-safe", 10.0, 10.0, "reject", 0.99)],
        previous_timestamp_s=0.95,
    )

    assert len(logs) == 1
    assert logs[0].ack_code == AckCode.NACK_SAFE
    assert logs[0].scheduler_state == "SAFE"
    assert logs[0].actuator_command_issued is False
