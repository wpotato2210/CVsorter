from __future__ import annotations

from pathlib import Path

import pytest

from coloursorter.ingest.adapter import IngestPayloadAdapter, IngestValidationError
from coloursorter.ingest.boundary import IngestBoundary
from coloursorter.ingest.drop_policy import DeterministicDropPolicy
from coloursorter.ingest.frame_id_policy import MonotonicFrameIdError, MonotonicFrameIdPolicy
from coloursorter.ingest.queue import BoundedFifoQueue
from coloursorter.model import ObjectDetection

CONTRACT = Path("contracts/frame_schema.json")


def _payload(frame_id: int = 1) -> dict[str, object]:
    return {
        "frame_id": frame_id,
        "timestamp": 1.0,
        "image_shape": [4, 4, 3],
        "detections": [ObjectDetection("d", 1.0, 1.0, "accept", 0.1)],
    }


def test_ingest_payload_adapter_validates_required_keys() -> None:
    """Error path: missing required fields fail contract validation."""
    adapter = IngestPayloadAdapter(CONTRACT)
    with pytest.raises(IngestValidationError, match="Missing required field"):
        adapter.adapt({"timestamp": 1.0, "image_shape": [4, 4, 3]})


def test_ingest_boundary_drop_oldest_reports_dropped_frame_id() -> None:
    """Boundary: bounded queue drop policy deterministically evicts oldest frame."""
    boundary = IngestBoundary(contract_path=CONTRACT, capacity=1, drop_policy=DeterministicDropPolicy.DROP_OLDEST)
    first = boundary.submit(_payload(1))
    second = boundary.submit(_payload(2))
    assert first.accepted is True
    assert second.dropped_frame_id == 1


def test_monotonic_frame_policy_rejects_regression() -> None:
    """Error path: frame IDs must increase strictly."""
    policy = MonotonicFrameIdPolicy()
    policy.validate(5)
    with pytest.raises(MonotonicFrameIdError):
        policy.validate(5)


def test_bounded_queue_drop_newest_rejects_new_item() -> None:
    """Boundary: DROP_NEWEST keeps existing queue item and rejects incoming one."""
    queue = BoundedFifoQueue[int](capacity=1)
    assert queue.push(1, DeterministicDropPolicy.DROP_OLDEST).accepted is True
    rejected = queue.push(2, DeterministicDropPolicy.DROP_NEWEST)
    assert rejected.accepted is False
    assert queue.pop() == 1
