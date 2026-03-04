from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .artifact import TrainArtifactMetadata, save_train_artifact_metadata
from .augmentation import AugmentationPolicy, augment_dataset


@dataclass(frozen=True)
class BaselineTrainingResult:
    augmented_count: int
    metadata_path: Path


def run_baseline_training(
    frames: list[np.ndarray],
    artifact_path: str | Path,
    model_name: str = "baseline-model-stub",
    label_space: tuple[str, ...] = ("accept", "reject"),
    input_width_px: int = 320,
    input_height_px: int = 240,
    score_threshold: float = 0.5,
    seed: int = 42,
) -> BaselineTrainingResult:
    if not frames:
        raise ValueError("frames must be non-empty")
    if any(not isinstance(frame, np.ndarray) for frame in frames):
        raise TypeError("frames must contain numpy.ndarray items")
    if any(frame.ndim < 2 for frame in frames):
        raise ValueError("frames must be at least 2D arrays")
    if not model_name.strip():
        raise ValueError("model_name must be non-empty")
    if not label_space or any(not label.strip() for label in label_space):
        raise ValueError("label_space must contain non-empty labels")
    if input_width_px <= 0 or input_height_px <= 0:
        raise ValueError("input dimensions must be positive")
    if not (0.0 <= score_threshold <= 1.0):
        raise ValueError("score_threshold must be in [0.0, 1.0]")

    augmented = augment_dataset(frames, policy=AugmentationPolicy(), seed=seed)
    metadata = TrainArtifactMetadata(
        artifact_version="v1",
        model_name=model_name,
        label_space=label_space,
        input_width_px=input_width_px,
        input_height_px=input_height_px,
        score_threshold=score_threshold,
    )
    metadata_path = save_train_artifact_metadata(artifact_path, metadata)
    return BaselineTrainingResult(augmented_count=len(augmented), metadata_path=metadata_path)
