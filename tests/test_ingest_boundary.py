from __future__ import annotations

from pathlib import Path

import pytest

from coloursorter.ingest import (
    DeterministicDropPolicy,
    IngestBoundary,
    IngestPayloadAdapter,
    IngestValidationError,
    MonotonicFrameIdError,
    MonotonicFrameIdPolicy,
)
from coloursorter.model import ObjectDetection


CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "frame_schema.json"


def _payload(frame_id: int, timestamp: float = 0.1) -> dict[str, object]:
    return {
        "frame_id": frame_id,
        "timestamp": timestamp,
        "image_shape": [480, 640, 3],
        "detections": [ObjectDetection(object_id="o1", centroid_x_px=1.0, centroid_y_px=2.0, classification="accept")],
        "previous_timestamp_s": max(0.0, timestamp - 0.1),
    }


def test_monotonic_frame_ids_enforced() -> None:
    policy = MonotonicFrameIdPolicy()
    policy.validate(1)
    policy.validate(2)
    with pytest.raises(MonotonicFrameIdError):
        policy.validate(2)


def test_drop_policy_is_deterministic_drop_oldest() -> None:
    boundary = IngestBoundary(CONTRACT, capacity=2, drop_policy=DeterministicDropPolicy.DROP_OLDEST)
    boundary.submit(_payload(1, 0.1))
    boundary.submit(_payload(2, 0.2))
    result = boundary.submit(_payload(3, 0.3))
    assert result.accepted is True
    assert result.dropped_frame_id == 1

    first = boundary.next_cycle_input()
    second = boundary.next_cycle_input()
    assert first is not None and second is not None
    assert (first.frame.frame_id, second.frame.frame_id) == (2, 3)


def test_schema_validation_rejects_bad_payload() -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    with pytest.raises(IngestValidationError):
        adapter.adapt({"frame_id": "bad", "timestamp": 0.1, "image_shape": [1, 2, 3]})


@pytest.mark.parametrize(
    "payload",
    [
        {"frame_id": -1, "timestamp": 0.1, "image_shape": [1, 2, 3]},
        {"frame_id": 1, "timestamp": -0.1, "image_shape": [1, 2, 3]},
        {"frame_id": 1, "timestamp": float("nan"), "image_shape": [1, 2, 3]},
        {"frame_id": 1, "timestamp": 0.1, "image_shape": [0, 2, 3]},
        {"frame_id": 1, "timestamp": 0.1, "image_shape": [1, 2, 2]},
        {"frame_id": 1, "timestamp": 0.1, "image_shape": [1, 2, 3], "previous_timestamp_s": 0.2},
    ],
)
def test_schema_validation_rejects_invalid_ranges_and_shapes(payload: dict[str, object]) -> None:
    adapter = IngestPayloadAdapter(CONTRACT)
    with pytest.raises(IngestValidationError):
        adapter.adapt(payload)


def test_scheduler_boundary_timing_semantics_preserved() -> None:
    boundary = IngestBoundary(CONTRACT, capacity=1)
    boundary.submit(_payload(9, 1.5))
    cycle_input = boundary.next_cycle_input()
    assert cycle_input is not None
    assert cycle_input.frame.timestamp_s == pytest.approx(1.5)
    assert cycle_input.previous_timestamp_s == pytest.approx(1.4)
