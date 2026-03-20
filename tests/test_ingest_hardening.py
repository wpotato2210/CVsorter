from __future__ import annotations

from pathlib import Path

import pytest

from coloursorter.ingest.adapter import IngestPayloadAdapter, IngestValidationError
from coloursorter.model import ObjectDetection

CONTRACT = Path("contracts/frame_schema.json")


def _payload() -> dict[str, object]:
    return {
        "frame_id": 1,
        "timestamp": 1.0,
        "image_shape": [8, 8, 3],
        "detections": [ObjectDetection("det-1", 1.0, 2.0, "accept", 0.75)],
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("frame_id", True, "frame_id must be integer"),
        ("timestamp", False, "timestamp must be number"),
        ("previous_timestamp_s", 2.0, "previous_timestamp_s must be <= timestamp"),
        ("image_shape", [8, 8, 1], "image_shape channels must be exactly 3"),
    ],
)
def test_ingest_adapter_rejects_invalid_scalar_contract_values(
    field: str,
    value: object,
    message: str,
) -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    payload = _payload()
    payload[field] = value

    with pytest.raises(IngestValidationError, match=message):
        adapter.adapt(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("captured_monotonic_s", -0.01, "captured_monotonic_s must be >= 0.0"),
        ("detect_latency_ms", float("nan"), "detect_latency_ms must be finite"),
    ],
)
def test_ingest_adapter_rejects_invalid_optional_numbers(
    field: str,
    value: object,
    message: str,
) -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    payload = _payload()
    payload[field] = value

    with pytest.raises(IngestValidationError, match=message):
        adapter.adapt(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("run_id", "   ", "run_id must be non-empty when provided"),
        ("detection_model_version", 17, "detection_model_version must be string"),
    ],
)
def test_ingest_adapter_rejects_invalid_optional_strings(
    field: str,
    value: object,
    message: str,
) -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    payload = _payload()
    payload[field] = value

    with pytest.raises(IngestValidationError, match=message):
        adapter.adapt(payload)


def test_ingest_adapter_rejects_non_object_detection_entries() -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    payload = _payload()
    payload["detections"] = [{"object_id": "not-valid"}]

    with pytest.raises(IngestValidationError, match="detections must contain ObjectDetection objects"):
        adapter.adapt(payload)


def test_ingest_adapter_accepts_deterministic_hardening_fields() -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    payload = _payload()
    payload.update(
        {
            "run_id": "run-001",
            "test_batch_id": "batch-001",
            "frame_snapshot_path": "snapshots/frame-000001.png",
            "captured_monotonic_s": 1.0,
            "detect_latency_ms": 2.5,
            "detection_provider_version": "provider-v1",
            "detection_model_version": "model-v2",
            "active_config_hash": "abc123",
            "ground_truth_by_object_id": {"det-1": "accept"},
            "preprocess_metrics": {"normalized": True, "exposure_ms": 3.2},
        }
    )

    adapted = adapter.adapt(payload)

    assert adapted.frame.frame_id == 1
    assert adapted.frame.image_height_px == 8
    assert adapted.frame.image_width_px == 8
    assert len(adapted.detections) == 1
    assert adapted.run_id == "run-001"
    assert adapted.preprocess_metrics == {"normalized": True, "exposure_ms": 3.2}
