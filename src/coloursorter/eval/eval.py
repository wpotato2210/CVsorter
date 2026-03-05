from __future__ import annotations

import torch
from torch import nn

from coloursorter.config.pipeline_config import PipelineConfig
from coloursorter.dataset import DeterministicFrameDataset, ensure_dataset_nonempty
from coloursorter.preprocess import preprocess_rgb_frame


def evaluate_accuracy(model: nn.Module, dataset: DeterministicFrameDataset, config: PipelineConfig) -> float:
    """Contract: input RGB images -> output accuracy in [0,1]."""
    ensure_dataset_nonempty(dataset)
    model = model.to(config.device)
    model.eval()
    correct = 0
    with torch.no_grad():
        for image_hwc, label in zip(dataset.images_hwc, dataset.labels):
            tensor_bchw = preprocess_rgb_frame(image_hwc, config)
            logits = model(tensor_bchw)
            prediction = int(torch.argmax(logits, dim=1).item())
            correct += int(prediction == label)
    return correct / len(dataset)
