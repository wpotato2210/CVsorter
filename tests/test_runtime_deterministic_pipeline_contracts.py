from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from coloursorter.actuator_iface import build_actuator_command, build_estop_command
from coloursorter.config import DEFAULT_PIPELINE_CONFIG
from coloursorter.dataset import DeterministicFrameDataset, ensure_dataset_nonempty
from coloursorter.model import DeterministicConvNet
from coloursorter.preprocess import preprocess_rgb_frame
from coloursorter.scheduler import TimingSample, evaluate_timing_acceptance, schedule_actuation


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_preprocess_enforces_image_and_tensor_contracts() -> None:
    frame_hwc = np.zeros((224, 224, 3), dtype=np.uint8)
    tensor = preprocess_rgb_frame(frame_hwc, DEFAULT_PIPELINE_CONFIG)
    assert tensor.shape == (1, 3, 224, 224)
    assert tensor.device.type == DEFAULT_PIPELINE_CONFIG.device


def test_dataset_nonempty_assertion() -> None:
    dataset = DeterministicFrameDataset(images_hwc=tuple(), labels=tuple())
    with pytest.raises(ValueError, match="dataset nonempty"):
        ensure_dataset_nonempty(dataset)


def test_model_device_and_shape_contract() -> None:
    model = DeterministicConvNet(num_classes=3).to(DEFAULT_PIPELINE_CONFIG.device)
    batch = torch.zeros((1, 3, 224, 224), dtype=torch.float32, device=DEFAULT_PIPELINE_CONFIG.device)
    logits = model(batch)
    assert logits.shape == (1, 3)
    assert logits.device.type == DEFAULT_PIPELINE_CONFIG.device


def test_scheduler_acceptance_thresholds_and_estop_command() -> None:
    timing = TimingSample(
        frame_timestamp_ms=1000,
        pipeline_latency_ms=DEFAULT_PIPELINE_CONFIG.physical.timing.max_latency_ms,
        trigger_offset_ms=4,
        actuation_delay_ms=2,
    )
    scheduled = schedule_actuation(lane=1, timing=timing, config=DEFAULT_PIPELINE_CONFIG)
    assert scheduled.execute_at_ms == 1006

    acceptance = evaluate_timing_acceptance(
        pipeline_latency_ms=timing.pipeline_latency_ms,
        throughput_fps=DEFAULT_PIPELINE_CONFIG.physical.throughput.min_frames_per_second,
        estop_response_ms=DEFAULT_PIPELINE_CONFIG.physical.timing.estop_response_threshold_ms,
        config=DEFAULT_PIPELINE_CONFIG,
    )
    assert acceptance.latency_within_threshold
    assert acceptance.throughput_within_threshold
    assert acceptance.estop_within_threshold

    command = build_actuator_command(
        scheduled=scheduled,
        pulse_ms=DEFAULT_PIPELINE_CONFIG.physical.timing.min_actuator_pulse_ms,
        config=DEFAULT_PIPELINE_CONFIG,
    )
    assert command == (
        "ACT|lane=1|execute_at_ms=1006|pulse_ms="
        f"{DEFAULT_PIPELINE_CONFIG.physical.timing.min_actuator_pulse_ms}"
    )
    assert build_estop_command(frame_timestamp_ms=1000) == "ESTOP|frame_timestamp_ms=1000"


def test_runtime_config_and_telemetry_schemas_publish_required_fields() -> None:
    runtime_schema = json.loads((REPO_ROOT / "contracts" / "pipeline_runtime_config_schema.json").read_text())
    telemetry_schema = json.loads((REPO_ROOT / "contracts" / "pipeline_telemetry_schema.json").read_text())

    runtime_required = set(runtime_schema["required"])
    telemetry_required = set(telemetry_schema["required"])

    assert {"device", "image", "physical"}.issubset(runtime_required)
    assert {
        "frame_timestamp_ms",
        "pipeline_latency_ms",
        "trigger_offset_ms",
        "actuation_delay_ms",
        "throughput_fps",
        "estop_response_ms",
    }.issubset(telemetry_required)


def test_pipeline_config_validate_contract() -> None:
    DEFAULT_PIPELINE_CONFIG.validate()
