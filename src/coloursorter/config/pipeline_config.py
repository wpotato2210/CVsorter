from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimingConfig:
    """Deterministic timing contract in milliseconds."""

    fps_target: int
    max_latency_ms: int
    max_actuator_pulse_ms: int
    heartbeat_period_ms: int
    heartbeat_timeout_ms: int
    estop_response_threshold_ms: int


@dataclass(frozen=True)
class ThroughputConfig:
    """Deterministic throughput contract for acceptance checks."""

    min_frames_per_second: float


@dataclass(frozen=True)
class QueueConfig:
    queue_depth: int


@dataclass(frozen=True)
class ImageConfig:
    """I/O contract for camera frame preprocessing."""

    colour_format: str
    normalization_range: tuple[float, float]
    model_input_shape_hwc: tuple[int, int, int]


@dataclass(frozen=True)
class PhysicalConfig:
    """Physical and real-time parameters; runtime modules must only read from this object."""

    timing: TimingConfig
    throughput: ThroughputConfig
    queue: QueueConfig


@dataclass(frozen=True)
class PipelineConfig:
    device: str
    image: ImageConfig
    physical: PhysicalConfig

    def validate(self) -> None:
        """Runtime config guard for deterministic CV pipeline contracts."""
        min_norm, max_norm = self.image.normalization_range
        if self.image.colour_format not in {"RGB", "BGR"}:
            raise ValueError("image.colour_format must be RGB or BGR")
        if min_norm >= max_norm:
            raise ValueError("image.normalization_range must be strictly increasing")
        if self.image.model_input_shape_hwc[2] != 3:
            raise ValueError("image.model_input_shape_hwc must declare 3 channels")
        if self.physical.queue.queue_depth <= 0:
            raise ValueError("physical.queue.queue_depth must be > 0")
        if self.physical.timing.max_latency_ms <= 0:
            raise ValueError("physical.timing.max_latency_ms must be > 0")


DEFAULT_PIPELINE_CONFIG = PipelineConfig(
    device="cpu",
    image=ImageConfig(
        colour_format="RGB",
        normalization_range=(0.0, 1.0),
        model_input_shape_hwc=(224, 224, 3),
    ),
    physical=PhysicalConfig(
        timing=TimingConfig(
            fps_target=100,
            max_latency_ms=15,
            max_actuator_pulse_ms=1,
            heartbeat_period_ms=50,
            heartbeat_timeout_ms=150,
            estop_response_threshold_ms=10,
        ),
        throughput=ThroughputConfig(min_frames_per_second=100.0),
        queue=QueueConfig(queue_depth=8),
    ),
)
