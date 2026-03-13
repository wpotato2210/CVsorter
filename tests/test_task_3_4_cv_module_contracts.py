from __future__ import annotations

import numpy as np
import pytest
import torch

from coloursorter.actuator_iface.actuator_iface import build_actuator_command
from coloursorter.config.pipeline_config import DEFAULT_PIPELINE_CONFIG, RuntimeTimingSample
from coloursorter.dataset.dataset import DatasetNonemptyAssertionError, DeterministicFrameDataset, ensure_dataset_nonempty
from coloursorter.eval.eval import evaluate_accuracy
from coloursorter.infer.infer import infer_class
from coloursorter.model.model import DeterministicConvNet
from coloursorter.preprocess.preprocess import preprocess_rgb_frame
from coloursorter.scheduler.scheduler import schedule_actuation
from coloursorter.train.train import train_one_epoch


def _make_dataset() -> DeterministicFrameDataset:
    image_a = np.zeros((16, 16, 3), dtype=np.uint8)
    image_b = np.full((16, 16, 3), 255, dtype=np.uint8)
    return DeterministicFrameDataset(images_hwc=(image_a, image_b), labels=(0, 1))


def test_task_3_4_preprocess_contract_shape_tensor_device() -> None:
    image = np.full((16, 16, 3), 127, dtype=np.uint8)

    tensor_bchw = preprocess_rgb_frame(image, DEFAULT_PIPELINE_CONFIG)

    assert tuple(tensor_bchw.shape) == (1, 3, 16, 16)
    assert tensor_bchw.device == torch.device(DEFAULT_PIPELINE_CONFIG.device)
    assert tensor_bchw.dtype == torch.float32


def test_task_3_4_runtime_assertions_for_image_shape_and_dataset_nonempty() -> None:
    with pytest.raises(ValueError, match=r"image shape must be \(H,W,3\)"):
        preprocess_rgb_frame(np.zeros((16, 16), dtype=np.uint8), DEFAULT_PIPELINE_CONFIG)

    empty_dataset = DeterministicFrameDataset(images_hwc=tuple(), labels=tuple())
    with pytest.raises(DatasetNonemptyAssertionError, match="dataset nonempty assertion failed"):
        ensure_dataset_nonempty(empty_dataset)


def test_task_3_4_model_train_eval_infer_contracts_are_deterministic() -> None:
    torch.manual_seed(34)
    dataset = _make_dataset()
    model = DeterministicConvNet(num_classes=2)

    mean_loss = train_one_epoch(model, dataset, DEFAULT_PIPELINE_CONFIG)
    accuracy = evaluate_accuracy(model, dataset, DEFAULT_PIPELINE_CONFIG)
    prediction = infer_class(model, dataset.images_hwc[0], DEFAULT_PIPELINE_CONFIG)

    assert mean_loss >= 0.0
    assert 0.0 <= accuracy <= 1.0
    assert prediction in {0, 1}


def test_task_3_4_scheduler_and_actuator_use_runtime_timing_sample_contract() -> None:
    timing = RuntimeTimingSample(
        frame_timestamp_ms=1_000,
        pipeline_latency_ms=DEFAULT_PIPELINE_CONFIG.physical.timing.max_latency_ms,
        trigger_offset_ms=4,
        actuation_delay_ms=2,
    )

    scheduled = schedule_actuation(lane=1, timing=timing, config=DEFAULT_PIPELINE_CONFIG)
    command = build_actuator_command(
        scheduled=scheduled,
        pulse_ms=DEFAULT_PIPELINE_CONFIG.physical.timing.min_actuator_pulse_ms,
        config=DEFAULT_PIPELINE_CONFIG,
    )

    assert scheduled.execute_at_ms == (
        timing.frame_timestamp_ms + timing.trigger_offset_ms + timing.actuation_delay_ms
    )
    assert command == "ACT|lane=1|execute_at_ms=1006|pulse_ms=4"
