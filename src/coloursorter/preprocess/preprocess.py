from __future__ import annotations

import numpy as np
import torch

from coloursorter.config.pipeline_config import PipelineConfig


def preprocess_rgb_frame(frame_hwc: np.ndarray, config: PipelineConfig) -> torch.Tensor:
    """Input: RGB uint8 image (H,W,3). Output: float32 tensor (B,C,H,W)=(1,3,H,W) on config.device."""
    assert frame_hwc.ndim == 3 and frame_hwc.shape[2] == 3, "image shape must be (H,W,3)"
    assert config.image.model_input_shape_hwc[2] == 3, "configured input shape must declare 3 channels"
    if config.image.colour_format != "RGB":
        raise ValueError("preprocess_rgb_frame expects RGB input format")

    min_range, max_range = config.image.normalization_range
    if min_range >= max_range:
        raise ValueError("normalization_range must be strictly increasing")

    frame_float_hwc = frame_hwc.astype(np.float32) / 255.0
    frame_float_hwc = frame_float_hwc * (max_range - min_range) + min_range

    tensor_bchw = torch.from_numpy(frame_float_hwc).permute(2, 0, 1).unsqueeze(0).contiguous()
    assert tensor_bchw.ndim == 4 and tensor_bchw.shape[1] == 3, "tensor shape must be (B,C,H,W)"
    tensor_bchw = tensor_bchw.to(device=config.device, dtype=torch.float32)
    assert tensor_bchw.device.type == torch.device(config.device).type, "device match assertion failed"
    return tensor_bchw
