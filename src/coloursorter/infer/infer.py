from __future__ import annotations

import numpy as np
import torch
from torch import nn

from coloursorter.config.pipeline_config import PipelineConfig
from coloursorter.preprocess import preprocess_rgb_frame


def infer_class(model: nn.Module, image_hwc: np.ndarray, config: PipelineConfig) -> int:
    """Contract: RGB uint8 (H,W,3) -> class index int; tensor layout (B,C,H,W) on config.device."""
    model = model.to(config.device)
    model.eval()
    with torch.no_grad():
        tensor_bchw = preprocess_rgb_frame(image_hwc, config)
        assert tensor_bchw.ndim == 4 and tensor_bchw.shape[1] == 3, "tensor shape must be (B,C,H,W)"
        logits = model(tensor_bchw)
        assert logits.device.type == torch.device(config.device).type, "device match assertion failed"
        return int(torch.argmax(logits, dim=1).item())
