from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

from coloursorter.bench.runner import BenchRunner, BenchSafetyConfig
from coloursorter.bench.types import AckCode
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy.pipeline import PipelineResult, ScheduledDecision
from coloursorter.model import CentroidMM, DecisionPayload, ObjectDetection
from coloursorter.scheduler import build_scheduled_command

RUNNER_PATH = Path("src/coloursorter/bench/runner.py")


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


def test_phase2_task13_queue_age_equal_boundary_does_not_force_safe() -> None:
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    max_queue_age_ms = 20.0
    runner = BenchRunner(
        pipeline=_PipelineStub(),
        transport=_AckTransportStub(),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(max_queue_age_ms=max_queue_age_ms),
    )

    with patch("coloursorter.bench.runner.time.perf_counter") as perf_counter:
        perf_counter.side_effect = [
            100.02,
            100.02,
            100.03,
            100.03,
            100.031,
            100.031,
            100.035,
            100.04,
            100.045,
        ]
        log = runner.run_cycle(
            1,
            1.0,
            20,
            20,
            [detection],
            previous_timestamp_s=0.9,
            enqueued_monotonic_s=100.0,
        )[0]

    assert log.transport_sent is True
    assert log.over_budget is False
    assert log.fault_event == ""
    assert log.ack_code == AckCode.ACK
    assert log.actuator_command_issued is True


def test_phase2_task13_queue_age_guardrail_is_strictly_greater_than_budget() -> None:
    module = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"), filename=str(RUNNER_PATH))
    run_cycle = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "BenchRunner"
        for item in node.body
        if isinstance(item, ast.FunctionDef) and item.name == "run_cycle"
    )

    queue_age_guard = None
    for node in ast.walk(run_cycle):
        if isinstance(node, ast.If):
            check = ast.unparse(node.test)
            if check == "queue_age_ms > self._safety.max_queue_age_ms":
                queue_age_guard = node
                break

    assert queue_age_guard is not None
    body_source = "\n".join(ast.unparse(stmt) for stmt in queue_age_guard.body)
    assert "QUEUE_AGE_EXCEEDED" in body_source
    assert "command = None" in body_source


def test_phase2_task13_queue_age_above_boundary_forces_safe() -> None:
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    max_queue_age_ms = 20.0
    runner = BenchRunner(
        pipeline=_PipelineStub(),
        transport=_AckTransportStub(),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(max_queue_age_ms=max_queue_age_ms),
    )

    with patch("coloursorter.bench.runner.time.perf_counter") as perf_counter:
        perf_counter.side_effect = [
            100.022,
            100.022,
            100.03,
            100.03,
            100.031,
            100.031,
            100.035,
            100.04,
            100.045,
        ]
        log = runner.run_cycle(
            1,
            1.0,
            20,
            20,
            [detection],
            previous_timestamp_s=0.9,
            enqueued_monotonic_s=100.0,
        )[0]

    assert log.transport_sent is False
    assert log.over_budget is True
    assert log.fault_event == "QUEUE_AGE_EXCEEDED"
    assert log.ack_code == AckCode.NACK_SAFE
    assert log.actuator_command_issued is False
