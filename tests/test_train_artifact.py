from __future__ import annotations

import json

import pytest

from coloursorter.train import (
    TrainArtifactError,
    TrainArtifactMetadata,
    load_train_artifact_metadata,
    save_train_artifact_metadata,
)


def test_train_artifact_metadata_round_trip(tmp_path) -> None:
    artifact_path = tmp_path / "artifact.json"
    expected = TrainArtifactMetadata(
        artifact_version="v1",
        model_name="opencv_baseline",
        label_space=("accept", "reject"),
        input_width_px=640,
        input_height_px=480,
        score_threshold=0.55,
    )

    save_train_artifact_metadata(artifact_path, expected)
    loaded = load_train_artifact_metadata(artifact_path)

    assert loaded == expected


def test_train_artifact_metadata_rejects_invalid_threshold(tmp_path) -> None:
    artifact_path = tmp_path / "artifact_invalid.json"
    artifact_path.write_text(
        json.dumps(
            {
                "artifact_version": "v1",
                "model_name": "opencv_baseline",
                "label_space": ["accept", "reject"],
                "input_width_px": 640,
                "input_height_px": 480,
                "score_threshold": 1.2,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TrainArtifactError, match="score_threshold"):
        load_train_artifact_metadata(artifact_path)
