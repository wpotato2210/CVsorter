from __future__ import annotations

from dataclasses import dataclass

from coloursorter.config.pipeline_config import PipelineConfig


@dataclass(frozen=True)
class TimingSample:
    frame_timestamp_ms: int
    pipeline_latency_ms: int
    trigger_offset_ms: int
    actuation_delay_ms: int


@dataclass(frozen=True)
class ScheduledActuation:
    lane: int
    execute_at_ms: int


def schedule_actuation(lane: int, timing: TimingSample, config: PipelineConfig) -> ScheduledActuation:
    """Contract: deterministic schedule from timing model; all timing values in milliseconds."""
    assert timing.pipeline_latency_ms <= config.physical.timing.max_latency_ms
    execute_at_ms = timing.frame_timestamp_ms + timing.trigger_offset_ms + timing.actuation_delay_ms
    return ScheduledActuation(lane=lane, execute_at_ms=execute_at_ms)
