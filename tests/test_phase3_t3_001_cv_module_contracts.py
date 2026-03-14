from __future__ import annotations

import numpy as np
import pytest
import torch

from coloursorter.actuator_iface import build_actuator_command
from coloursorter.config import DEFAULT_PIPELINE_CONFIG
from coloursorter.config.pipeline_config import RuntimeTimingSample
from coloursorter.dataset import DeterministicFrameDataset, ensure_dataset_nonempty
from coloursorter.dataset.dataset import DatasetNonemptyAssertionError
from coloursorter.eval import evaluate_accuracy
from coloursorter.infer import infer_class
from coloursorter.model import DeterministicConvNet
from coloursorter.preprocess import preprocess_rgb_frame
from coloursorter.scheduler import schedule_actuation
from coloursorter.train import train_one_epoch


def _sample_image() -> np.ndarray:
    return np.full((8, 8, 3), 127, dtype=np.uint8)


def _sample_dataset() -> DeterministicFrameDataset:
    return DeterministicFrameDataset(images_hwc=(_sample_image(),), labels=(0,))


def test_t3_001_preprocess_and_model_tensor_contracts() -> None:
    config = DEFAULT_PIPELINE_CONFIG
    tensor_bchw = preprocess_rgb_frame(_sample_image(), config)

    assert tuple(tensor_bchw.shape) == (1, 3, 8, 8)
    assert tensor_bchw.device == torch.device(config.device)

    model = DeterministicConvNet(num_classes=2).to(config.device)
    logits = model(tensor_bchw)

    assert tuple(logits.shape) == (1, 2)
    assert logits.device == torch.device(config.device)


def test_t3_001_runtime_assertions_for_image_shape_and_dataset_nonempty() -> None:
    config = DEFAULT_PIPELINE_CONFIG
    bad_image = np.zeros((8, 8), dtype=np.uint8)
    with pytest.raises(ValueError, match=r"image shape must be \(H,W,3\)"):
        preprocess_rgb_frame(bad_image, config)

    empty_dataset = DeterministicFrameDataset(images_hwc=tuple(), labels=tuple())
    with pytest.raises(DatasetNonemptyAssertionError, match="dataset nonempty assertion failed"):
        ensure_dataset_nonempty(empty_dataset)


def test_t3_001_train_eval_infer_contracts() -> None:
    config = DEFAULT_PIPELINE_CONFIG
    dataset = _sample_dataset()
    model = DeterministicConvNet(num_classes=1)

    loss = train_one_epoch(model=model, dataset=dataset, config=config)
    accuracy = evaluate_accuracy(model=model, dataset=dataset, config=config)
    class_id = infer_class(model=model, image_hwc=_sample_image(), config=config)

    assert isinstance(loss, float)
    assert isinstance(accuracy, float)
    assert class_id == 0


def test_t3_001_scheduler_and_actuator_read_physical_config_values() -> None:
    config = DEFAULT_PIPELINE_CONFIG

    scheduled = schedule_actuation(
        lane=2,
        timing=RuntimeTimingSample(
            frame_timestamp_ms=100,
            pipeline_latency_ms=10,
            trigger_offset_ms=5,
            actuation_delay_ms=7,
        ),
        config=config,
    )
    assert scheduled.execute_at_ms == 112

    command = build_actuator_command(
        scheduled=scheduled,
        pulse_ms=config.physical.timing.min_actuator_pulse_ms,
        config=config,
    )
    assert command == "ACT|lane=2|execute_at_ms=112|pulse_ms=4"
