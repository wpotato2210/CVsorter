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
