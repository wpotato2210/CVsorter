from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import re
import torch

from coloursorter.calibration.mapping import CalibrationError, expected_calibration_hash, load_calibration
from coloursorter.config.pipeline_config import (
    ImageConfig,
    PhysicalConfig,
    PipelineConfig,
    QueueConfig,
    ThroughputConfig,
    TimingConfig,
)
from coloursorter.preprocess.preprocess import preprocess_rgb_frame

FIXTURES = Path(__file__).parent / "fixtures"


def _pipeline_config(
    *,
    colour_format: str = "RGB",
    normalization_range: tuple[float, float] = (0.0, 1.0),
    model_input_shape_hwc: tuple[int, int, int] = (4, 5, 3),
    device: str = "cpu",
) -> PipelineConfig:
    return PipelineConfig(
        device=device,
        image=ImageConfig(
            colour_format=colour_format,
            normalization_range=normalization_range,
            model_input_shape_hwc=model_input_shape_hwc,
        ),
        physical=PhysicalConfig(
            timing=TimingConfig(
                fps_target=100,
                max_latency_ms=15,
                min_actuator_pulse_ms=4,
                max_actuator_pulse_ms=40,
                heartbeat_period_ms=50,
                heartbeat_timeout_ms=150,
                estop_response_threshold_ms=10,
            ),
            throughput=ThroughputConfig(min_frames_per_second=100.0),
            queue=QueueConfig(queue_depth=8),
        ),
    )


def test_preprocess_locks_input_output_contracts() -> None:
    frame_hwc = np.array(
        [
            [[0, 127, 255], [64, 32, 16]],
            [[255, 128, 0], [10, 20, 30]],
        ],
        dtype=np.uint8,
    )
    config = _pipeline_config(normalization_range=(-1.0, 1.0), model_input_shape_hwc=(2, 2, 3))

    tensor_bchw = preprocess_rgb_frame(frame_hwc, config)

    assert tensor_bchw.shape == (1, 3, 2, 2)
    assert tensor_bchw.dtype == torch.float32
    assert tensor_bchw.device.type == "cpu"

    expected_hwc = frame_hwc.astype(np.float32) / 255.0
    expected_hwc = expected_hwc * 2.0 - 1.0
    expected_bchw = torch.from_numpy(expected_hwc).permute(2, 0, 1).unsqueeze(0).contiguous().to(torch.float32)
    assert torch.equal(tensor_bchw.cpu(), expected_bchw)


@pytest.mark.parametrize(
    ("frame_hwc", "config", "exc_type", "message"),
    [
        (
            np.zeros((2, 2), dtype=np.uint8),
            _pipeline_config(),
            ValueError,
            "image shape must be (H,W,3)",
        ),
        (
            np.zeros((2, 2, 3), dtype=np.float32),
            _pipeline_config(),
            TypeError,
            "image dtype must be uint8",
        ),
        (
            np.zeros((2, 2, 3), dtype=np.uint8),
            _pipeline_config(colour_format="BGR"),
            ValueError,
            "preprocess_rgb_frame expects RGB input format",
        ),
        (
            np.zeros((2, 2, 3), dtype=np.uint8),
            _pipeline_config(model_input_shape_hwc=(2, 2, 1)),
            ValueError,
            "configured input shape must declare 3 channels",
        ),
        (
            np.zeros((2, 2, 3), dtype=np.uint8),
            _pipeline_config(normalization_range=(1.0, 1.0)),
            ValueError,
            "normalization_range must be strictly increasing",
        ),
    ],
)
def test_preprocess_rejects_implicit_or_invalid_assumptions(
    frame_hwc: np.ndarray,
    config: PipelineConfig,
    exc_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exc_type, match=re.escape(message)):
        preprocess_rgb_frame(frame_hwc, config)


def test_preprocess_output_is_deterministic_for_identical_inputs() -> None:
    frame_hwc = np.arange(3 * 3 * 3, dtype=np.uint8).reshape(3, 3, 3)
    config = _pipeline_config(model_input_shape_hwc=(3, 3, 3))

    first = preprocess_rgb_frame(frame_hwc, config)
    second = preprocess_rgb_frame(frame_hwc, config)

    assert torch.equal(first, second)


def test_calibration_hash_contract_is_stable_for_mm_per_pixel_precision() -> None:
    mm_per_pixel = 0.123456789012

    assert expected_calibration_hash(mm_per_pixel) == "adf94188db2c74fc3266587d13431eab3af6c2ac1dd9abc9502cd55e6e1bc3c1"


def test_load_calibration_uses_verified_hash_and_deterministic_scaling() -> None:
    calibration = load_calibration(FIXTURES / "calibration_edge_valid.json")

    observed = [calibration.px_to_mm(512.5) for _ in range(5)]

    assert observed == [63.271604368649996] * 5


def test_load_calibration_rejects_tampered_hash() -> None:
    with pytest.raises(
        CalibrationError,
        match="Invalid calibration hash: expected deterministic SHA-256 of mm_per_pixel",
    ):
        load_calibration(FIXTURES / "calibration_edge_invalid_hash.json")
