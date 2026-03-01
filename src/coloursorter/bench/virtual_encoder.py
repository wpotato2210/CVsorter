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
    def belt_speed_mm_per_s(self) -> float:
        return 0.0 if self._fault_config.force_zero_speed else self._config.belt_speed_mm_per_s

    @property
    def last_pulse_timestamp_s(self) -> float | None:
        return self._last_pulse_timestamp_s

    def pulses_between(self, start_time_s: float, end_time_s: float) -> int:
        duration_s = max(0.0, end_time_s - start_time_s)
        if self._fault_config.force_zero_speed:
            return 0

        revolutions = (self._config.belt_speed_mm_per_s * duration_s) / self._config.pulley_circumference_mm
        produced_pulses = revolutions * self._config.pulses_per_revolution
        self._pulse_accumulator += produced_pulses
        pulses = int(self._pulse_accumulator)
        self._pulse_accumulator -= pulses

        if self._fault_config.force_missing_pulses:
            return 0
        if self._config.dropout_ratio <= 0.0:
            if pulses > 0:
                self._last_pulse_timestamp_s = end_time_s
            return pulses

        kept_ratio = max(0.0, min(1.0, 1.0 - self._config.dropout_ratio))
        adjusted_pulses = pulses * kept_ratio
        kept_integer = int(adjusted_pulses)
        self._pulse_accumulator += adjusted_pulses - kept_integer
        if kept_integer > 0:
            self._last_pulse_timestamp_s = end_time_s
        return kept_integer
