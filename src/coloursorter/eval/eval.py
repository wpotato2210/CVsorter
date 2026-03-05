from __future__ import annotations

import torch
from torch import nn

from coloursorter.config.pipeline_config import PipelineConfig
from coloursorter.dataset import DeterministicFrameDataset, ensure_dataset_nonempty
from coloursorter.preprocess import preprocess_rgb_frame


def evaluate_accuracy(model: nn.Module, dataset: DeterministicFrameDataset, config: PipelineConfig) -> float:
    """Contract: RGB (H,W,3) -> logits -> scalar accuracy in [0,1] on config.device."""
    ensure_dataset_nonempty(dataset)
    model = model.to(config.device)
    model.eval()
    correct = 0
    with torch.no_grad():
        for image_hwc, label in zip(dataset.images_hwc, dataset.labels):
            tensor_bchw = preprocess_rgb_frame(image_hwc, config)
            assert tensor_bchw.ndim == 4 and tensor_bchw.shape[1] == 3, "tensor shape must be (B,C,H,W)"
            logits = model(tensor_bchw)
            assert logits.device.type == torch.device(config.device).type, "device match assertion failed"
            prediction = int(torch.argmax(logits, dim=1).item())
            correct += int(prediction == label)
    return correct / len(dataset)
