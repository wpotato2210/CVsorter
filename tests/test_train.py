from __future__ import annotations

import numpy as np
import pytest

from coloursorter.train.artifact import TrainArtifactMetadata, load_train_artifact_metadata, save_train_artifact_metadata
from coloursorter.train.augmentation import AugmentationPolicy, augment_dataset
from coloursorter.train.baseline import run_baseline_training


def test_augment_dataset_is_deterministic_for_seed() -> None:
    """Normal path: repeated seeded augmentation emits identical outputs."""
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    out_a = augment_dataset([frame], policy=AugmentationPolicy(), seed=7)
    out_b = augment_dataset([frame], policy=AugmentationPolicy(), seed=7)
    assert len(out_a) == 4
    assert all(np.array_equal(a, b) for a, b in zip(out_a, out_b))


def test_artifact_metadata_roundtrip(tmp_path) -> None:
    """Normal path: metadata save/load preserves typed fields."""
    path = save_train_artifact_metadata(
        tmp_path / "artifact.json",
        TrainArtifactMetadata("v1", "demo", ("accept", "reject"), 32, 32, 0.5),
    )
    loaded = load_train_artifact_metadata(path)
    assert loaded.model_name == "demo"
    assert loaded.label_space == ("accept", "reject")


def test_run_baseline_training_rejects_empty_frames(tmp_path) -> None:
    """Error path: baseline training enforces non-empty frames."""
    with pytest.raises(ValueError, match="non-empty"):
        run_baseline_training([], artifact_path=tmp_path / "meta.json")
