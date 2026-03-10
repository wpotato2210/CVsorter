from __future__ import annotations

from types import SimpleNamespace

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
        self._result = PipelineResult(decisions=(decision,), schedule_commands=(command,), scheduled_events=(ScheduledDecision("det-1", decision, command),))

    def run(self, frame, detections):
        return self._result


class _TransportStub:
    def __init__(self, ack: AckCode = AckCode.ACK, round_trip_ms: float = 2.0) -> None:
        self.ack = ack
        self.round_trip_ms = round_trip_ms

    def send(self, _command):
        return SimpleNamespace(
            queue_depth=0,
            scheduler_state="IDLE",
            mode="AUTO",
            queue_cleared=False,
            round_trip_ms=self.round_trip_ms,
            ack_code=self.ack,
            nack_code=None,
            nack_detail=None,
        )


def _runner(safety: BenchSafetyConfig | None = None, ack: AckCode = AckCode.ACK) -> BenchRunner:
    return BenchRunner(
        pipeline=_PipelineStub(),
        transport=_TransportStub(ack=ack),
        encoder=VirtualEncoder(EncoderConfig(2048, 100.0, 200.0)),
        safety=safety,
    )


def test_run_cycle_emits_acknowledged_log_entry() -> None:
    """Normal path: schedule command is sent and acknowledged."""
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    logs = _runner().run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)
    assert len(logs) == 1
    assert logs[0].transport_sent is True
    assert logs[0].transport_acknowledged is True
    assert logs[0].fault_event == ""


def test_run_cycle_suppresses_duplicate_command_for_same_object() -> None:
    """Boundary path: duplicate frame/object command key is not resent."""
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    runner = _runner()
    assert runner.run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)[0].transport_sent is True
    second = runner.run_cycle(1, 1.1, 20, 20, [detection], previous_timestamp_s=1.0)[0]
    assert second.transport_sent is False


def test_run_cycle_marks_queue_age_fault_and_skips_send() -> None:
    """Error/safety path: over-aged queue forces safe skip."""
    safety = BenchSafetyConfig(max_queue_age_ms=0.0)
    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 0.9)
    log = _runner(safety=safety).run_cycle(
        1,
        1.0,
        20,
        20,
        [detection],
        previous_timestamp_s=0.9,
        enqueued_monotonic_s=1.0,
    )[0]
    assert log.fault_event == "QUEUE_AGE_EXCEEDED"
    assert log.transport_sent is False


def test_summarize_handles_empty_and_fault_recovery() -> None:
    """Summary path: empty logs and mixed ack transitions are computed deterministically."""
    empty = BenchRunner.summarize(())
    assert empty.reject_reliability == 1.0

    detection = ObjectDetection("det-1", 10.0, 10.0, "reject", 1.0)
    nack_log = _runner(ack=AckCode.NACK_SAFE).run_cycle(1, 1.0, 20, 20, [detection], previous_timestamp_s=0.9)[0]
    ack_log = _runner(ack=AckCode.ACK).run_cycle(2, 2.0, 20, 20, [detection], previous_timestamp_s=1.9)[0]
    summary = BenchRunner.summarize((nack_log, ack_log))
    assert summary.safe_transitions >= 1
    assert summary.recovered_from_safe is True
