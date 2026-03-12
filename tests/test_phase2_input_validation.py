from __future__ import annotations

from pathlib import Path

import re

import pytest

from coloursorter.ingest.adapter import IngestPayloadAdapter, IngestValidationError

_CONTRACT = Path("contracts/frame_schema.json")


def _valid_payload() -> dict[str, object]:
    return {
        "frame_id": 1,
        "timestamp": 1.0,
        "image_shape": [10, 12, 3],
        "detections": [],
        "previous_timestamp_s": 0.5,
    }


@pytest.mark.parametrize(
    ("image_shape", "error_message"),
    [
        ([10, 12], "image_shape must be integer triplet [height, width, channels]"),
        ([10, 12, 1], "image_shape channels must be exactly 3 (BGR H,W,3)"),
        ([0, 12, 3], "image_shape height and width must be > 0"),
    ],
)
def test_ingest_rejects_invalid_frame_shapes_deterministically(image_shape: list[int], error_message: str) -> None:
    adapter = IngestPayloadAdapter(_CONTRACT)
    payload = _valid_payload()
    payload["image_shape"] = image_shape

    with pytest.raises(IngestValidationError, match=re.escape(error_message)):
        adapter.adapt(payload)


def test_ingest_rejects_negative_timestamp() -> None:
    adapter = IngestPayloadAdapter(_CONTRACT)
    payload = _valid_payload()
    payload["timestamp"] = -0.01

    with pytest.raises(IngestValidationError, match="timestamp must be >= 0"):
        adapter.adapt(payload)


def test_ingest_rejects_out_of_order_timestamp() -> None:
    adapter = IngestPayloadAdapter(_CONTRACT)
    payload = _valid_payload()
    payload["previous_timestamp_s"] = 2.0

    with pytest.raises(IngestValidationError, match="previous_timestamp_s must be <= timestamp"):
        adapter.adapt(payload)


def test_ingest_rejects_malformed_protocol_payload_type() -> None:
    adapter = IngestPayloadAdapter(_CONTRACT)

    with pytest.raises(IngestValidationError, match="payload must be a mapping"):
        adapter.adapt("not-a-payload")  # type: ignore[arg-type]
