from __future__ import annotations

import numpy as np
import pytest

from coloursorter.deploy.detection import (
    CaptureBaselineConfig,
    DetectionError,
    ModelStubDetectionConfig,
    ModelStubDetectionProvider,
    PreprocessConfig,
    _normalize_frame,
    _validate_detection_output,
    _validate_frame,
    capture_fault_reason,
)
from coloursorter.model import ObjectDetection


def test_validate_frame_rejects_invalid_inputs() -> None:
    """Error path: frame validation enforces ndarray shape and dtype contract."""
    with pytest.raises(DetectionError):
        _validate_frame(None)
    with pytest.raises(DetectionError):
        _validate_frame(np.zeros((4, 4), dtype=np.uint8))
    with pytest.raises(DetectionError):
        _validate_frame(np.zeros((4, 4, 3), dtype=np.float32))


def test_normalize_frame_noop_when_disabled() -> None:
    """Boundary: preprocess disabled returns original frame and identity gains."""
    frame = np.full((2, 2, 3), 100, dtype=np.uint8)
    out, metrics = _normalize_frame(frame, PreprocessConfig(enable_normalization=False))
    assert np.array_equal(out, frame)
    assert metrics["exposure_gain"] == 1.0


def test_capture_fault_reason_covers_threshold_failures() -> None:
    """Error path: capture baseline flags low luma and clipping conditions."""
    baseline = CaptureBaselineConfig(min_luma=10.0, max_luma=20.0, max_exposure_gain=1.1, max_clipped_ratio=0.01)
    assert capture_fault_reason({"luma_after": 5.0}, baseline) == "capture_luma_low"
    assert capture_fault_reason({"luma_after": 30.0}, baseline) == "capture_luma_high"
    assert capture_fault_reason({"luma_after": 12.0, "exposure_gain": 5.0}, baseline) == "capture_exposure_gain_high"


def test_model_stub_provider_applies_reject_threshold_and_clamps_score() -> None:
    """Normal path: model stub converts predictor output into deterministic detection payload."""
    provider = ModelStubDetectionProvider(
        predictor=lambda _f: [{"object_id": "x", "label": "reject", "confidence": 2.0}],
        config=ModelStubDetectionConfig(reject_threshold=0.5),
    )
    detections = provider.detect(np.zeros((2, 2, 3), dtype=np.uint8))
    assert detections[0].classification == "reject"
    assert detections[0].infection_score == 1.0


def test_validate_detection_output_rejects_duplicate_ids() -> None:
    """Error path: duplicate object IDs are rejected."""
    repeated = [
        ObjectDetection("same", 0.0, 0.0, "accept", 0.1),
        ObjectDetection("same", 1.0, 1.0, "accept", 0.2),
    ]
    with pytest.raises(DetectionError, match="duplicate object_id"):
        _validate_detection_output(repeated)
