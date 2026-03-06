from __future__ import annotations

import numpy as np
import pytest
import torch

from coloursorter.actuator_iface import validate_actuation_pulse_ms
from coloursorter.config import DEFAULT_PIPELINE_CONFIG
from coloursorter.dataset import DeterministicFrameDataset, ensure_dataset_nonempty
from coloursorter.preprocess import preprocess_rgb_frame
from coloursorter.scheduler import TimingSample, schedule_actuation


def test_preprocess_rejects_non_uint8_frame() -> None:
    image = np.zeros((8, 8, 3), dtype=np.float32)
    with pytest.raises(TypeError, match="dtype"):
        preprocess_rgb_frame(image, DEFAULT_PIPELINE_CONFIG)


def test_dataset_rejects_invalid_dtype() -> None:
    bad = (np.zeros((8, 8, 3), dtype=np.float32),)
    with pytest.raises(TypeError, match="dtype"):
        DeterministicFrameDataset(images_hwc=bad, labels=(0,))


def test_dataset_nonempty_raises_value_error() -> None:
    ds = DeterministicFrameDataset(images_hwc=(), labels=())
    with pytest.raises(ValueError, match="nonempty"):
        ensure_dataset_nonempty(ds)


def test_schedule_actuation_rejects_negative_timing() -> None:
    timing = TimingSample(
        frame_timestamp_ms=1,
        pipeline_latency_ms=-1,
        trigger_offset_ms=0,
        actuation_delay_ms=0,
    )
    with pytest.raises(ValueError, match="pipeline_latency_ms"):
        schedule_actuation(0, timing, DEFAULT_PIPELINE_CONFIG)


def test_validate_actuation_pulse_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="must be > 0"):
        validate_actuation_pulse_ms(0, DEFAULT_PIPELINE_CONFIG)
    with pytest.raises(ValueError, match="max_actuator_pulse_ms"):
        validate_actuation_pulse_ms(
            DEFAULT_PIPELINE_CONFIG.physical.timing.max_actuator_pulse_ms + 1,
            DEFAULT_PIPELINE_CONFIG,
        )


def test_preprocess_places_tensor_on_configured_device() -> None:
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    tensor = preprocess_rgb_frame(image, DEFAULT_PIPELINE_CONFIG)
    assert tensor.shape == (1, 3, 4, 4)
    assert tensor.device == torch.device(DEFAULT_PIPELINE_CONFIG.device)
