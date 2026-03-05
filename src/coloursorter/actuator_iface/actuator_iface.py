from __future__ import annotations

from coloursorter.config.pipeline_config import PipelineConfig
from coloursorter.scheduler.scheduler import ScheduledActuation


def validate_actuation_pulse_ms(pulse_ms: int, config: PipelineConfig) -> None:
    assert pulse_ms <= config.physical.timing.max_actuator_pulse_ms


def build_actuator_command(scheduled: ScheduledActuation, pulse_ms: int, config: PipelineConfig) -> str:
    """Contract: emits deterministic wire command string for actuator dispatch."""
    validate_actuation_pulse_ms(pulse_ms, config)
    return f"ACT|lane={scheduled.lane}|execute_at_ms={scheduled.execute_at_ms}|pulse_ms={pulse_ms}"
