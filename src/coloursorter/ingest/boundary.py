from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapter import IngestCycleInput, IngestPayloadAdapter
from .drop_policy import DeterministicDropPolicy
from .frame_id_policy import MonotonicFrameIdPolicy
from .queue import BoundedFifoQueue, QueuePushResult


@dataclass(frozen=True)
class IngestEnqueueResult:
    accepted: bool
    dropped_frame_id: int | None


class IngestBoundary:
    def __init__(
        self,
        contract_path: str | Path,
        capacity: int,
        drop_policy: DeterministicDropPolicy = DeterministicDropPolicy.DROP_OLDEST,
    ) -> None:
        self._adapter = IngestPayloadAdapter(contract_path)
        self._queue: BoundedFifoQueue[IngestCycleInput] = BoundedFifoQueue(capacity=capacity)
        self._frame_policy = MonotonicFrameIdPolicy()
        self._drop_policy = drop_policy

    def submit(self, payload: dict[str, Any]) -> IngestEnqueueResult:
        adapted = self._adapter.adapt(payload)
        self._frame_policy.validate(adapted.frame.frame_id)
        result: QueuePushResult[IngestCycleInput] = self._queue.push(adapted, self._drop_policy)
        dropped_frame_id = result.dropped_item.frame.frame_id if result.dropped_item is not None else None
        return IngestEnqueueResult(accepted=result.accepted, dropped_frame_id=dropped_frame_id)

    def next_cycle_input(self) -> IngestCycleInput | None:
        return self._queue.pop()
