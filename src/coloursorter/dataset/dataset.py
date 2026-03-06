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
        for image_hwc in self.images_hwc:
            if image_hwc.ndim != 3 or image_hwc.shape[2] != 3:
                raise ValueError("image shape must be (H,W,3)")
            if image_hwc.dtype != np.uint8:
                raise TypeError("image dtype must be uint8")

    def __len__(self) -> int:
        return len(self.images_hwc)

    def __getitem__(self, index: int) -> tuple[np.ndarray, int]:
        image_hwc = self.images_hwc[index]
        label = self.labels[index]
        if image_hwc.ndim != 3 or image_hwc.shape[2] != 3:
            raise ValueError("image shape must be (H,W,3)")
        if image_hwc.dtype != np.uint8:
            raise TypeError("image dtype must be uint8")
        return image_hwc, label


def ensure_dataset_nonempty(dataset: DeterministicFrameDataset) -> None:
    if len(dataset) <= 0:
        raise ValueError("dataset nonempty assertion failed")
