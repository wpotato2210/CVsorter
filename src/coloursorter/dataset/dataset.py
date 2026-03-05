from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DeterministicFrameDataset:
    """I/O contract: images are RGB uint8 arrays (H,W,3), labels are integer class ids."""

    images_hwc: tuple[np.ndarray, ...]
    labels: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.images_hwc) != len(self.labels):
            raise ValueError("dataset images and labels must have the same length")

    def __len__(self) -> int:
        return len(self.images_hwc)

    def __getitem__(self, index: int) -> tuple[np.ndarray, int]:
        image_hwc = self.images_hwc[index]
        label = self.labels[index]
        assert image_hwc.ndim == 3 and image_hwc.shape[2] == 3, "image shape must be (H,W,3)"
        return image_hwc, label


def ensure_dataset_nonempty(dataset: DeterministicFrameDataset) -> None:
    assert len(dataset) > 0, "dataset nonempty assertion failed"
