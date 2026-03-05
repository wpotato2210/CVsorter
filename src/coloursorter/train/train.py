from __future__ import annotations

import torch
from torch import nn

from coloursorter.config.pipeline_config import PipelineConfig
from coloursorter.dataset import DeterministicFrameDataset, ensure_dataset_nonempty
from coloursorter.preprocess import preprocess_rgb_frame


def train_one_epoch(
    model: nn.Module,
    dataset: DeterministicFrameDataset,
    config: PipelineConfig,
) -> float:
    """Contract: RGB (H,W,3) -> preprocess -> model tensor (B,C,H,W) on config.device; returns mean CE loss."""
    ensure_dataset_nonempty(dataset)
    model = model.to(config.device)
    model.train()
    optimizer = torch.optim.SGD(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    total_loss = 0.0
    for image_hwc, label in zip(dataset.images_hwc, dataset.labels):
        tensor_bchw = preprocess_rgb_frame(image_hwc, config)
        assert tensor_bchw.ndim == 4 and tensor_bchw.shape[1] == 3, "tensor shape must be (B,C,H,W)"
        logits = model(tensor_bchw)
        target = torch.tensor([label], dtype=torch.long, device=config.device)
        assert logits.device.type == target.device.type, "device match assertion failed"
        loss = criterion(logits, target)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        total_loss += float(loss.item())
    return total_loss / len(dataset)
