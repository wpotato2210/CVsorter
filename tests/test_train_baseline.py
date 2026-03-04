from __future__ import annotations

import numpy as np
import pytest

from coloursorter.train import load_train_artifact_metadata, run_baseline_training


def test_run_baseline_training_writes_metadata_and_augments(tmp_path) -> None:
    frame = np.full((16, 16, 3), 32, dtype=np.uint8)
    result = run_baseline_training(
        frames=[frame],
        artifact_path=tmp_path / "baseline_artifact.json",
        model_name="opencv_baseline",
        label_space=("accept", "reject"),
        input_width_px=16,
        input_height_px=16,
        score_threshold=0.6,
        seed=7,
    )

    metadata = load_train_artifact_metadata(result.metadata_path)
    assert result.augmented_count == 4
    assert metadata.model_name == "opencv_baseline"
    assert metadata.score_threshold == 0.6


@pytest.mark.parametrize(
    ("kwargs", "error_type", "message"),
    [
        ({"frames": []}, ValueError, "frames must be non-empty"),
        ({"frames": ["not-array"]}, TypeError, "numpy.ndarray"),
        ({"frames": [np.array(7, dtype=np.uint8)]}, ValueError, "at least 2D"),
        ({"model_name": "   "}, ValueError, "model_name must be non-empty"),
        ({"label_space": ("accept", "")}, ValueError, "label_space"),
        ({"input_width_px": 0}, ValueError, "input dimensions"),
        ({"score_threshold": 1.1}, ValueError, "score_threshold"),
    ],
)
def test_run_baseline_training_rejects_invalid_inputs(kwargs, error_type, message, tmp_path) -> None:
    base_kwargs = {
        "frames": [np.full((8, 8, 3), 64, dtype=np.uint8)],
        "artifact_path": tmp_path / "artifact.json",
    }
    base_kwargs.update(kwargs)

    with pytest.raises(error_type, match=message):
        run_baseline_training(**base_kwargs)
