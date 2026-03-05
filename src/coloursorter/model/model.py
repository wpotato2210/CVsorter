from __future__ import annotations

import torch
from torch import nn


class DeterministicConvNet(nn.Module):
    """Input tensor shape: (B,C,H,W) with C=3. Output logits: (B,num_classes)."""

    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.head = nn.Linear(32, num_classes)

    def forward(self, tensor_bchw: torch.Tensor) -> torch.Tensor:
        assert tensor_bchw.ndim == 4 and tensor_bchw.shape[1] == 3, "tensor shape must be (B,C,H,W)"
        features = self.backbone(tensor_bchw)
        logits = self.head(features.flatten(start_dim=1))
        return logits
