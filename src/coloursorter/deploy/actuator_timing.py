from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActuatorCalibration:
    offset_mm: float
    estimated_latency_ms: float
    sample_size: int


class ActuatorTimingCalibrator:
    def __init__(self, min_offset_mm: float = 0.0, max_offset_mm: float = 1000.0) -> None:
        self._min_offset_mm = min_offset_mm
        self._max_offset_mm = max_offset_mm

    def calibrate(
        self,
        latency_samples_ms: list[float],
        belt_speed_mm_s: float,
    ) -> ActuatorCalibration:
        if not latency_samples_ms:
            return ActuatorCalibration(offset_mm=0.0, estimated_latency_ms=0.0, sample_size=0)

        estimated_latency_ms = sum(latency_samples_ms) / len(latency_samples_ms)
        raw_offset_mm = max(0.0, belt_speed_mm_s * (estimated_latency_ms / 1000.0))
        offset_mm = min(self._max_offset_mm, max(self._min_offset_mm, raw_offset_mm))
        return ActuatorCalibration(
            offset_mm=offset_mm,
            estimated_latency_ms=estimated_latency_ms,
            sample_size=len(latency_samples_ms),
        )
