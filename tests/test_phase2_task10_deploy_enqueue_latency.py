from __future__ import annotations

import ast
import time
from pathlib import Path
from types import SimpleNamespace

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


class _SlowTransportStub:
    def __init__(self, sleep_s: float) -> None:
        self._sleep_s = sleep_s

    def send(self, _command):
        time.sleep(self._sleep_s)
        return SimpleNamespace(
            queue_depth=0,
            scheduler_state="IDLE",
            mode="AUTO",
            queue_cleared=False,
            round_trip_ms=2.0,
            ack_code=AckCode.ACK,
            nack_code=None,
            nack_detail=None,
        )


def _runner(send_budget_ms: float, transport_sleep_s: float) -> BenchRunner:
    return BenchRunner(
        pipeline=_PipelineStub(),
        transport=_SlowTransportStub(sleep_s=transport_sleep_s),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(send_budget_ms=send_budget_ms),
    )


def test_phase2_task10_enqueue_path_marks_safe_on_send_budget_exceeded() -> None:
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    log = _runner(send_budget_ms=0.01, transport_sleep_s=0.02).run_cycle(
        1,
        1.0,
        20,
        20,
        [detection],
        previous_timestamp_s=0.9,
    )[0]

    assert log.transport_sent is True
    assert log.fault_event == "SEND_BUDGET_EXCEEDED"
    assert log.over_budget is True
    assert log.actuator_command_issued is False
    assert log.ack_code == AckCode.NACK_SAFE


def test_phase2_task10_enqueue_guardrail_is_strictly_greater_than_budget() -> None:
    module = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"), filename=str(RUNNER_PATH))
    run_cycle = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "BenchRunner"
        for item in node.body
        if isinstance(item, ast.FunctionDef) and item.name == "run_cycle"
    )

    send_budget_guard = None
    for node in ast.walk(run_cycle):
        if isinstance(node, ast.If):
            check = ast.unparse(node.test)
            if check == "transport_latency_ms > self._safety.send_budget_ms":
                send_budget_guard = node
                break

    assert send_budget_guard is not None
    body_source = "\n".join(ast.unparse(stmt) for stmt in send_budget_guard.body)
    assert "SEND_BUDGET_EXCEEDED" in body_source
    assert "AckCode.NACK_SAFE" in body_source
