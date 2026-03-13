from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest
import torch

from coloursorter.actuator_iface import build_actuator_command, validate_actuation_pulse_ms
from coloursorter.config import DEFAULT_PIPELINE_CONFIG
from coloursorter.config.pipeline_config import RuntimeTimingSample
from coloursorter.dataset import DeterministicFrameDataset, ensure_dataset_nonempty
from coloursorter.eval import evaluate_accuracy
from coloursorter.infer import infer_class
from coloursorter.model import DeterministicConvNet
from coloursorter.preprocess import preprocess_rgb_frame
from coloursorter.scheduler import schedule_actuation
from coloursorter.train import train_one_epoch


RUNTIME_MODULES: tuple[Path, ...] = (
    Path("src/coloursorter/scheduler/scheduler.py"),
    Path("src/coloursorter/actuator_iface/actuator_iface.py"),
)


def _sample_image() -> np.ndarray:
    return np.zeros((8, 8, 3), dtype=np.uint8)


def test_runtime_timing_sample_fields_are_stable() -> None:
    sample = RuntimeTimingSample(
        frame_timestamp_ms=100,
        pipeline_latency_ms=3,
        trigger_offset_ms=7,
        actuation_delay_ms=2,
    )
    assert sample.frame_timestamp_ms == 100
    assert sample.pipeline_latency_ms == 3
    assert sample.trigger_offset_ms == 7
    assert sample.actuation_delay_ms == 2


def test_preprocess_runtime_assertions_hold() -> None:
    with pytest.raises(ValueError, match="image shape"):
        preprocess_rgb_frame(np.zeros((8, 8), dtype=np.uint8), DEFAULT_PIPELINE_CONFIG)

    tensor = preprocess_rgb_frame(_sample_image(), DEFAULT_PIPELINE_CONFIG)
    assert tensor.shape == (1, 3, 8, 8)
    assert tensor.device == torch.device(DEFAULT_PIPELINE_CONFIG.device)


def test_dataset_model_train_eval_infer_contracts() -> None:
    dataset = DeterministicFrameDataset(images_hwc=(_sample_image(),), labels=(0,))
    ensure_dataset_nonempty(dataset)

    model = DeterministicConvNet(num_classes=1)
    loss = train_one_epoch(model=model, dataset=dataset, config=DEFAULT_PIPELINE_CONFIG)
    assert loss >= 0.0

    accuracy = evaluate_accuracy(model=model, dataset=dataset, config=DEFAULT_PIPELINE_CONFIG)
    assert 0.0 <= accuracy <= 1.0

    class_id = infer_class(model=model, image_hwc=_sample_image(), config=DEFAULT_PIPELINE_CONFIG)
    assert class_id == 0


def test_scheduler_and_actuator_use_configured_timing() -> None:
    timing = RuntimeTimingSample(
        frame_timestamp_ms=10,
        pipeline_latency_ms=1,
        trigger_offset_ms=11,
        actuation_delay_ms=3,
    )
    scheduled = schedule_actuation(lane=2, timing=timing, config=DEFAULT_PIPELINE_CONFIG)
    assert scheduled.execute_at_ms == 24

    validate_actuation_pulse_ms(
        DEFAULT_PIPELINE_CONFIG.physical.timing.min_actuator_pulse_ms,
        DEFAULT_PIPELINE_CONFIG,
    )
    cmd = build_actuator_command(
        scheduled,
        DEFAULT_PIPELINE_CONFIG.physical.timing.min_actuator_pulse_ms,
        DEFAULT_PIPELINE_CONFIG,
    )
    assert cmd == "ACT|lane=2|execute_at_ms=24|pulse_ms=4"


def test_runtime_modules_do_not_embed_physical_threshold_literals() -> None:
    for path in RUNTIME_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        numeric_literals = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and node.value not in (0, 1)
        ]
        assert numeric_literals == [], f"physical constants should be sourced from config in {path}"
