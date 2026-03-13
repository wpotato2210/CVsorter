from __future__ import annotations

import numpy as np
import pytest
import torch

from coloursorter.actuator_iface.actuator_iface import build_actuator_command, validate_actuation_pulse_ms
from coloursorter.config.pipeline_config import DEFAULT_PIPELINE_CONFIG, RuntimeTimingSample
from coloursorter.dataset.dataset import (
    DatasetNonemptyAssertionError,
    DeterministicFrameDataset,
    ensure_dataset_nonempty,
)
from coloursorter.infer.infer import infer_class
from coloursorter.model.model import DeterministicConvNet
from coloursorter.preprocess.preprocess import preprocess_rgb_frame
from coloursorter.scheduler.scheduler import schedule_actuation


def _valid_rgb_frame() -> np.ndarray:
    return np.zeros((16, 16, 3), dtype=np.uint8)


def test_phase3_2_preprocess_tensor_contract_shape_and_device() -> None:
    tensor_bchw = preprocess_rgb_frame(_valid_rgb_frame(), DEFAULT_PIPELINE_CONFIG)

    assert tuple(tensor_bchw.shape) == (1, 3, 16, 16)
    assert tensor_bchw.device == torch.device(DEFAULT_PIPELINE_CONFIG.device)
    assert tensor_bchw.dtype == torch.float32


def test_phase3_2_dataset_nonempty_assertion_contract() -> None:
    dataset = DeterministicFrameDataset(images_hwc=(), labels=())

    with pytest.raises(DatasetNonemptyAssertionError, match="dataset nonempty assertion failed"):
        ensure_dataset_nonempty(dataset)


def test_phase3_2_infer_and_model_tensor_shape_contract() -> None:
    model = DeterministicConvNet(num_classes=3)

    class_id = infer_class(model, _valid_rgb_frame(), DEFAULT_PIPELINE_CONFIG)

    assert class_id in {0, 1, 2}


@pytest.mark.parametrize(
    ("timing", "expected_execute_at_ms"),
    [
        (RuntimeTimingSample(100, 3, 5, 7), 112),
        (RuntimeTimingSample(250, 1, 0, 4), 254),
    ],
)
def test_phase3_2_scheduler_and_actuator_config_boundaries(
    timing: RuntimeTimingSample,
    expected_execute_at_ms: int,
) -> None:
    scheduled = schedule_actuation(lane=2, timing=timing, config=DEFAULT_PIPELINE_CONFIG)

    assert scheduled.execute_at_ms == expected_execute_at_ms
    validate_actuation_pulse_ms(DEFAULT_PIPELINE_CONFIG.physical.timing.min_actuator_pulse_ms, DEFAULT_PIPELINE_CONFIG)

    command = build_actuator_command(
        scheduled,
        DEFAULT_PIPELINE_CONFIG.physical.timing.max_actuator_pulse_ms,
        DEFAULT_PIPELINE_CONFIG,
    )
    assert command.startswith("ACT|lane=2|execute_at_ms=")
