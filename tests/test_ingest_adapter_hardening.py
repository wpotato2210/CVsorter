from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.ingest.adapter import IngestPayloadAdapter, IngestValidationError
from coloursorter.model import ObjectDetection


CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "frame_schema.json"


def test_contract_validation_ignores_unrelated_required_keys(tmp_path: Path) -> None:
    contract_path = tmp_path / "wire_contract.json"
    contract_path.write_text(json.dumps({"required": ["frame_id", "timestamp", "image_shape", "wire_payload"]}), encoding="utf-8")

    adapter = IngestPayloadAdapter(contract_path)
    adapted = adapter.adapt({"frame_id": 1, "timestamp": 0.1, "image_shape": [10, 20, 3]})

    assert adapted.frame.frame_id == 1
    assert adapted.frame.image_height_px == 10
    assert adapted.frame.image_width_px == 20


@pytest.mark.parametrize(
    "payload",
    [
        {"frame_id": True, "timestamp": 0.1, "image_shape": [1, 2, 3]},
        {"frame_id": 1, "timestamp": False, "image_shape": [1, 2, 3]},
    ],
)
def test_schema_validation_rejects_boolean_numeric_fields(payload: dict[str, object]) -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    with pytest.raises(IngestValidationError):
        adapter.adapt(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"frame_id": 1, "timestamp": 0.1, "image_shape": [1, 2, 3], "captured_monotonic_s": float("inf")},
        {"frame_id": 1, "timestamp": 0.1, "image_shape": [1, 2, 3], "detect_latency_ms": float("inf")},
    ],
)
def test_schema_validation_rejects_non_finite_optional_numbers(payload: dict[str, object]) -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    with pytest.raises(IngestValidationError):
        adapter.adapt(payload)


def test_schema_validation_rejects_non_object_detection_entries() -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    with pytest.raises(IngestValidationError, match="detections must contain ObjectDetection objects"):
        adapter.adapt(
            {
                "frame_id": 3,
                "timestamp": 0.3,
                "image_shape": [8, 8, 3],
                "detections": [
                    ObjectDetection("ok", 1.0, 1.0, "accept", 0.9),
                    {"object_id": "bad"},
                ],
            }
        )
