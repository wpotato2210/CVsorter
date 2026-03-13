from __future__ import annotations

from types import SimpleNamespace

import pytest

from coloursorter.bench.runner import BenchRunner, BenchSafetyConfig
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


class _TransportStub:
    def send(self, _command):
        return SimpleNamespace(
            queue_depth=0,
            scheduler_state="IDLE",
            mode="AUTO",
            queue_cleared=False,
            round_trip_ms=2.0,
            ack_code="ACK",
            nack_code=None,
            nack_detail=None,
        )


def _build_runner(safety: BenchSafetyConfig) -> BenchRunner:
    return BenchRunner(
        pipeline=_PipelineStub(),
        transport=_TransportStub(),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=safety,
    )


def test_phase3_4_timebase_reference_reflects_selected_strategy() -> None:
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    log_default = _build_runner(BenchSafetyConfig()).run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)[0]
    log_offset = _build_runner(
        BenchSafetyConfig(timebase_strategy="host_to_mcu_offset", host_to_mcu_offset_ms=25.0)
    ).run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)[0]

    assert log_default.timebase_reference == "encoder_epoch"
    assert log_offset.timebase_reference == "host_to_mcu_offset"


def test_phase3_4_host_to_mcu_offset_deterministically_shifts_trigger_timestamp() -> None:
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    base_log = _build_runner(BenchSafetyConfig()).run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)[0]
    offset_ms = 30.0
    offset_log = _build_runner(
        BenchSafetyConfig(timebase_strategy="host_to_mcu_offset", host_to_mcu_offset_ms=offset_ms)
    ).run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)[0]

    assert (offset_log.trigger_timestamp_s - base_log.trigger_timestamp_s) == pytest.approx(offset_ms / 1000.0)
