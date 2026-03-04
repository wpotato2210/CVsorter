"""Deterministic training utilities for ColourSorter."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class TrainingExample:
    """Single labeled feature vector used for training."""

    features: tuple[float, ...]
    label: str


@dataclass(frozen=True)
class TrainedModel:
    """Centroid-based model artifact with deterministic class ordering."""

    feature_dim: int
    labels: tuple[str, ...]
    class_centroids: tuple[tuple[float, ...], ...]

    def predict(self, features: Sequence[float]) -> str:
        """Predict label for one feature vector using nearest centroid."""
        if len(features) != self.feature_dim:
            raise ValueError(f"Expected {self.feature_dim} features, got {len(features)}")

        best_idx = 0
        best_distance = math.inf
        for idx, centroid in enumerate(self.class_centroids):
            distance = _squared_l2(features, centroid)
            if distance < best_distance:
                best_distance = distance
                best_idx = idx
        return self.labels[best_idx]


def train_model(examples: Sequence[TrainingExample]) -> TrainedModel:
    """Train a deterministic centroid classifier from labeled examples.

    Input contract:
      - examples is non-empty.
      - all examples have the same feature length >= 1.
      - labels are non-empty strings.

    Output contract:
      - labels are sorted lexicographically.
      - class_centroids align index-wise with labels.
      - centroids are arithmetic means per class.
    """
    if not examples:
        raise ValueError("examples must not be empty")

    feature_dim = len(examples[0].features)
    if feature_dim == 0:
        raise ValueError("feature vectors must not be empty")

    sums: dict[str, list[float]] = {}
    counts: dict[str, int] = {}

    for example in examples:
        if not example.label:
            raise ValueError("example labels must not be empty")
        if len(example.features) != feature_dim:
            raise ValueError("all feature vectors must have the same length")

        running = sums.setdefault(example.label, [0.0] * feature_dim)
        for idx, value in enumerate(example.features):
            running[idx] += value
        counts[example.label] = counts.get(example.label, 0) + 1

    labels = tuple(sorted(sums))
    centroids: list[tuple[float, ...]] = []
    for label in labels:
        count = counts[label]
        centroids.append(tuple(total / count for total in sums[label]))

    return TrainedModel(
        feature_dim=feature_dim,
        labels=labels,
        class_centroids=tuple(centroids),
    )


def load_examples_jsonl(path: str | Path) -> tuple[TrainingExample, ...]:
    """Load training examples from JSONL.

    Each line must contain: {"features": [number, ...], "label": "..."}.
    """
    loaded: list[TrainingExample] = []
    for index, raw_line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        try:
            label = str(payload["label"])
            feature_values = tuple(float(v) for v in payload["features"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid example on line {index}") from exc
        loaded.append(TrainingExample(features=feature_values, label=label))
    return tuple(loaded)


def save_model_json(model: TrainedModel, path: str | Path) -> None:
    """Save trained model artifact as deterministic JSON."""
    payload = {
        "feature_dim": model.feature_dim,
        "labels": list(model.labels),
        "class_centroids": [list(centroid) for centroid in model.class_centroids],
    }
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def train_entrypoint(input_path: str | Path, output_path: str | Path) -> TrainedModel:
    """Minimal reproducible training entrypoint for scripts/CLI usage."""
    examples = load_examples_jsonl(input_path)
    model = train_model(examples)
    save_model_json(model, output_path)
    return model


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: python -m coloursorter.train <input.jsonl> <model.json>."""
    args = list(argv or [])
    if len(args) != 2:
        raise SystemExit("Usage: python -m coloursorter.train <input.jsonl> <model.json>")
    train_entrypoint(args[0], args[1])
    return 0


def _squared_l2(left: Sequence[float], right: Sequence[float]) -> float:
    return sum((float(a) - float(b)) ** 2 for a, b in zip(left, right, strict=True))


__all__ = [
    "TrainingExample",
    "TrainedModel",
    "train_model",
    "load_examples_jsonl",
    "save_model_json",
    "train_entrypoint",
    "main",
]
