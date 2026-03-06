from __future__ import annotations

from dataclasses import dataclass

from coloursorter.config.pipeline_config import PipelineConfig, RuntimeTimingSample


# Backward-compatible export; canonical definition lives in config.
TimingSample = RuntimeTimingSample


@dataclass(frozen=True)
class ScheduledActuation:
    lane: int
    execute_at_ms: int


@dataclass(frozen=True)
class TimingAcceptance:
    latency_within_threshold: bool
    throughput_within_threshold: bool
    estop_within_threshold: bool


def schedule_actuation(lane: int, timing: RuntimeTimingSample, config: PipelineConfig) -> ScheduledActuation:
    """Contract: deterministic schedule from timing model; all timing values in milliseconds."""
    if timing.frame_timestamp_ms < 0:
        raise ValueError("frame_timestamp_ms must be >= 0")
    if timing.pipeline_latency_ms < 0:
        raise ValueError("pipeline_latency_ms must be >= 0")
    if timing.trigger_offset_ms < 0:
        raise ValueError("trigger_offset_ms must be >= 0")
    if timing.actuation_delay_ms < 0:
        raise ValueError("actuation_delay_ms must be >= 0")
    if timing.pipeline_latency_ms > config.physical.timing.max_latency_ms:
        raise ValueError("pipeline_latency_ms exceeds physical.timing.max_latency_ms")
    execute_at_ms = timing.frame_timestamp_ms + timing.trigger_offset_ms + timing.actuation_delay_ms
    return ScheduledActuation(lane=lane, execute_at_ms=execute_at_ms)


def evaluate_timing_acceptance(
    pipeline_latency_ms: int,
    throughput_fps: float,
    estop_response_ms: int,
    config: PipelineConfig,
) -> TimingAcceptance:
    """Acceptance contract: validates latency, throughput, and E-STOP response against config thresholds."""
    return TimingAcceptance(
        latency_within_threshold=pipeline_latency_ms <= config.physical.timing.max_latency_ms,
        throughput_within_threshold=throughput_fps >= config.physical.throughput.min_frames_per_second,
        estop_within_threshold=estop_response_ms <= config.physical.timing.estop_response_threshold_ms,
    )
