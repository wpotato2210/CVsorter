from __future__ import annotations

import numpy as np
import pytest
import torch
from torch import nn

from coloursorter.config.pipeline_config import DEFAULT_PIPELINE_CONFIG, PipelineConfig
from coloursorter.infer.infer import infer_class


class _BadModel(nn.Module):
    def forward(self, _tensor):
        return torch.zeros((1, 2), device="meta")


class _GoodModel(nn.Module):
    def forward(self, _tensor):
        return torch.tensor([[0.1, 0.9]], dtype=torch.float32)


def _config() -> PipelineConfig:
    return PipelineConfig(device=DEFAULT_PIPELINE_CONFIG.device, image=DEFAULT_PIPELINE_CONFIG.image, physical=DEFAULT_PIPELINE_CONFIG.physical)


def test_infer_class_returns_argmax_index() -> None:
    """Normal path: infer returns deterministic argmax index."""
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    assert infer_class(_GoodModel(), image, _config()) == 1


def test_infer_class_raises_when_model_device_mismatches() -> None:
    """Error path: logits device mismatch raises RuntimeError."""
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    with pytest.raises(RuntimeError, match="device match"):
        infer_class(_BadModel(), image, _config())
