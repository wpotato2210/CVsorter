from __future__ import annotations

import random
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class AugmentationPolicy:
    rotation_min_deg: int = -15
    rotation_max_deg: int = 15
    alpha_min: float = 0.8
    alpha_max: float = 1.2
    beta_min: int = -20
    beta_max: int = 20
    blur_kernel_sizes: tuple[int, ...] = (3, 5)


def apply_rotation(frame: np.ndarray, angle_deg: int) -> np.ndarray:
    height, width = frame.shape[:2]
    if not hasattr(cv2, "getRotationMatrix2D") or not hasattr(cv2, "warpAffine"):
        return frame.copy()
    matrix = cv2.getRotationMatrix2D((width / 2.0, height / 2.0), angle_deg, 1.0)
    return cv2.warpAffine(frame, matrix, (width, height))


def adjust_brightness_contrast(frame: np.ndarray, alpha: float, beta: int) -> np.ndarray:
    if not hasattr(cv2, "convertScaleAbs"):
        scaled = frame.astype(np.float32) * alpha + beta
        return np.clip(scaled, 0, 255).astype(np.uint8)
    return cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)


def apply_blur(frame: np.ndarray, kernel_size: int) -> np.ndarray:
    if not hasattr(cv2, "GaussianBlur"):
        return frame.copy()
    return cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)


def augment_dataset(frames: list[np.ndarray], policy: AugmentationPolicy | None = None, seed: int = 42) -> list[np.ndarray]:
    rng = random.Random(seed)
    policy = policy or AugmentationPolicy()
    augmented: list[np.ndarray] = []
    for frame in frames:
        augmented.append(frame)
        augmented.append(apply_rotation(frame, angle_deg=rng.randint(policy.rotation_min_deg, policy.rotation_max_deg)))
        augmented.append(
            adjust_brightness_contrast(
                frame,
                alpha=rng.uniform(policy.alpha_min, policy.alpha_max),
                beta=rng.randint(policy.beta_min, policy.beta_max),
            )
        )
        augmented.append(apply_blur(frame, kernel_size=rng.choice(policy.blur_kernel_sizes)))
    return augmented
