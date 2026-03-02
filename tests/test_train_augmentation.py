from __future__ import annotations

import numpy as np

from coloursorter.train import augment_dataset


def test_augment_dataset_is_deterministic_with_seed() -> None:
    frame = np.full((32, 32, 3), 128, dtype=np.uint8)
    aug_a = augment_dataset([frame], seed=123)
    aug_b = augment_dataset([frame], seed=123)
    assert len(aug_a) == 4
    assert len(aug_b) == 4
    for left, right in zip(aug_a, aug_b):
        assert np.array_equal(left, right)
