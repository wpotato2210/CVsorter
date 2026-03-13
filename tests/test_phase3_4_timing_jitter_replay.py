from __future__ import annotations

from dataclasses import dataclass

from coloursorter.bench.runner import BenchRunner, BenchSafetyConfig
from coloursorter.bench.virtual_encoder import EncoderConfig, VirtualEncoder
from coloursorter.deploy.pipeline import PipelineResult, ScheduledDecision
from coloursorter.model import CentroidMM, DecisionPayload, ObjectDetection
from coloursorter.scheduler import build_scheduled_command


@dataclass(frozen=True)
class _Response:
    queue_depth: int
    scheduler_state: str
    mode: str
    queue_cleared: bool
    round_trip_ms: float
    ack_code: str
    nack_code: int | None
    nack_detail: str | None


class _PipelineStub:
    def __init__(self) -> None:
        decision = DecisionPayload(
            frame_id=1,
            object_id="det-1",
            lane=0,
            centroid_mm=CentroidMM(x_mm=10.0, y_mm=5.0),
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


class _JitterTransportStub:
    def __init__(self, round_trip_ms: tuple[float, ...]) -> None:
        self._round_trip_ms = round_trip_ms
        self._idx = 0

    def send(self, _command) -> _Response:
        latency = self._round_trip_ms[self._idx % len(self._round_trip_ms)]
        self._idx += 1
        return _Response(
            queue_depth=0,
            scheduler_state="IDLE",
            mode="AUTO",
            queue_cleared=False,
            round_trip_ms=latency,
            ack_code="ACK",
            nack_code=None,
            nack_detail=None,
        )


def _run_replay(round_trip_ms: tuple[float, ...]) -> tuple[float, float, float, bool, bool]:
    runner = BenchRunner(
        pipeline=_PipelineStub(),
        transport=_JitterTransportStub(round_trip_ms),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=BenchSafetyConfig(timebase_strategy="host_to_mcu_offset", host_to_mcu_offset_ms=20.0),
    )
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.95)
    first_log = runner.run_cycle(
        frame_id=7,
        timestamp_s=1.0,
        image_height_px=32,
        image_width_px=32,
        detections=[detection],
        previous_timestamp_s=0.9,
    )[0]
    second_log = runner.run_cycle(
        frame_id=8,
        timestamp_s=1.1,
        image_height_px=32,
        image_width_px=32,
        detections=[detection],
        previous_timestamp_s=1.0,
    )[0]
    return (
        first_log.trigger_timestamp_s,
        first_log.trigger_reference_s,
        second_log.rtt_jitter_ms,
        second_log.jitter_warn,
        second_log.jitter_critical,
    )


def test_phase3_4_jitter_replay_is_deterministic_for_identical_seeded_sequence() -> None:
    seeded_sequence = (2.0, 7.5, 12.0)

    first = _run_replay(seeded_sequence)
    second = _run_replay(seeded_sequence)

    assert first == second


def test_phase3_4_trigger_schedule_is_stable_under_transport_jitter_variants() -> None:
    baseline = _run_replay((2.0, 2.0))
    high_jitter = _run_replay((2.0, 9.0))

    assert high_jitter[0] == baseline[0]
    assert high_jitter[1] == baseline[1]
    assert high_jitter[2] > baseline[2]
    assert high_jitter[3] is True
    assert high_jitter[4] is False
