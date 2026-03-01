from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


class TrainArtifactError(ValueError):
    pass


@dataclass(frozen=True)
class TrainArtifactMetadata:
    artifact_version: str
    model_name: str
    label_space: tuple[str, ...]
    input_width_px: int
    input_height_px: int
    score_threshold: float


def save_train_artifact_metadata(path: str | Path, metadata: TrainArtifactMetadata) -> Path:
    target = Path(path)
    payload = asdict(metadata)
    payload["label_space"] = list(metadata.label_space)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_train_artifact_metadata(path: str | Path) -> TrainArtifactMetadata:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        artifact_version = str(raw["artifact_version"]).strip()
        model_name = str(raw["model_name"]).strip()
        label_space = tuple(str(label).strip() for label in raw["label_space"])
        input_width_px = int(raw["input_width_px"])
        input_height_px = int(raw["input_height_px"])
        score_threshold = float(raw["score_threshold"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TrainArtifactError("Invalid train artifact metadata payload") from exc

    if not artifact_version:
        raise TrainArtifactError("artifact_version must be non-empty")
    if not model_name:
        raise TrainArtifactError("model_name must be non-empty")
    if not label_space or any(not label for label in label_space):
        raise TrainArtifactError("label_space must contain non-empty labels")
    if input_width_px <= 0 or input_height_px <= 0:
        raise TrainArtifactError("input dimensions must be positive")
    if not (0.0 <= score_threshold <= 1.0):
        raise TrainArtifactError("score_threshold must be in [0.0, 1.0]")

    return TrainArtifactMetadata(
        artifact_version=artifact_version,
        model_name=model_name,
        label_space=label_space,
        input_width_px=input_width_px,
        input_height_px=input_height_px,
        score_threshold=score_threshold,
    )
