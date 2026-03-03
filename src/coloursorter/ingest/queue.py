from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Generic, TypeVar

from .drop_policy import DeterministicDropPolicy

T = TypeVar("T")


@dataclass(frozen=True)
class QueuePushResult(Generic[T]):
    accepted: bool
    dropped_item: T | None


class BoundedFifoQueue(Generic[T]):
    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Queue capacity must be > 0")
        self._capacity = capacity
        self._items: Deque[T] = deque()

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._items)

    def push(self, item: T, policy: DeterministicDropPolicy) -> QueuePushResult[T]:
        if len(self._items) < self._capacity:
            self._items.append(item)
            return QueuePushResult(accepted=True, dropped_item=None)

        if policy == DeterministicDropPolicy.DROP_OLDEST:
            dropped = self._items.popleft()
            self._items.append(item)
            return QueuePushResult(accepted=True, dropped_item=dropped)

        if policy == DeterministicDropPolicy.DROP_NEWEST:
            return QueuePushResult(accepted=False, dropped_item=item)

        raise ValueError(f"Unsupported drop policy: {policy}")

    def pop(self) -> T | None:
        if not self._items:
            return None
        return self._items.popleft()
