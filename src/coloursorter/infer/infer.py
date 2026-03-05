from __future__ import annotations

import torch
from torch import nn

from coloursorter.config.pipeline_config import PipelineConfig
from coloursorter.preprocess import preprocess_rgb_frame


def infer_class(model: nn.Module, image_hwc, config: PipelineConfig) -> int:
    """Contract: RGB (H,W,3) -> class index int; tensor layout (B,C,H,W)."""
    model = model.to(config.device)
    model.eval()
    with torch.no_grad():
        tensor_bchw = preprocess_rgb_frame(image_hwc, config)
        logits = model(tensor_bchw)
        return int(torch.argmax(logits, dim=1).item())
