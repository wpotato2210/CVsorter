from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EncoderConfig:
    pulses_per_revolution: int
    belt_speed_mm_per_s: float
    pulley_circumference_mm: float
    dropout_ratio: float = 0.0


@dataclass(frozen=True)
class EncoderFaultConfig:
    force_zero_speed: bool = False
    force_missing_pulses: bool = False


class VirtualEncoder:
    def __init__(self, config: EncoderConfig, fault_config: EncoderFaultConfig | None = None) -> None:
        self._config = config
        self._fault_config = fault_config or EncoderFaultConfig()
        self._pulse_accumulator = 0.0
        self._last_pulse_timestamp_s: float | None = None

    @property
    def mm_per_pulse(self) -> float:
        return self._config.pulley_circumference_mm / self._config.pulses_per_revolution

    @property
    def seconds_per_pulse(self) -> float:
        belt_speed_mm_s = self.belt_speed_mm_per_s
        if belt_speed_mm_s <= 0.0:
            return 0.0
        return self.mm_per_pulse / belt_speed_mm_s

    @property
    def belt_speed_mm_per_s(self) -> float:
        return 0.0 if self._fault_config.force_zero_speed else self._config.belt_speed_mm_per_s

    @property
    def last_pulse_timestamp_s(self) -> float | None:
        return self._last_pulse_timestamp_s

    def resolve_trigger_generation_timestamp(self, start_time_s: float) -> float:
        return self._last_pulse_timestamp_s if self._last_pulse_timestamp_s is not None else start_time_s

    def project_trigger_timestamp(
        self,
        trigger_generation_s: float,
        trigger_distance_mm: float,
        schedule_time_s: float,
    ) -> float:
        belt_speed_mm_s = self.belt_speed_mm_per_s
        if belt_speed_mm_s <= 0.0:
            return trigger_generation_s

        trigger_distance_pulses = trigger_distance_mm / self.mm_per_pulse
        travel_time_s = trigger_distance_pulses * self.seconds_per_pulse
        return trigger_generation_s + schedule_time_s + travel_time_s

    def pulses_between(self, start_time_s: float, end_time_s: float) -> int:
        duration_s = max(0.0, end_time_s - start_time_s)
        if self._fault_config.force_zero_speed:
            return 0

        revolutions = (self._config.belt_speed_mm_per_s * duration_s) / self._config.pulley_circumference_mm
        produced_pulses = revolutions * self._config.pulses_per_revolution
        starting_accumulator = self._pulse_accumulator
        self._pulse_accumulator += produced_pulses
        pulses = int(self._pulse_accumulator)
        self._pulse_accumulator -= pulses
        last_generated_pulse_timestamp_s: float | None = None
        if produced_pulses > 0.0 and pulses > 0:
            pulse_progress = (pulses - starting_accumulator) / produced_pulses
            last_generated_pulse_timestamp_s = start_time_s + min(1.0, max(0.0, pulse_progress)) * duration_s

        if self._fault_config.force_missing_pulses:
            return 0
        if self._config.dropout_ratio <= 0.0:
            if pulses > 0:
                self._last_pulse_timestamp_s = last_generated_pulse_timestamp_s
            return pulses

        kept_ratio = max(0.0, min(1.0, 1.0 - self._config.dropout_ratio))
        adjusted_pulses = pulses * kept_ratio
        kept_integer = int(adjusted_pulses)
        self._pulse_accumulator += adjusted_pulses - kept_integer
        if kept_integer > 0:
            self._last_pulse_timestamp_s = last_generated_pulse_timestamp_s
        return kept_integer
