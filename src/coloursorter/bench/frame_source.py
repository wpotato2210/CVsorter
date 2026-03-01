from __future__ import annotations

from typing import Protocol

from .types import BenchFrame


class FrameSourceError(RuntimeError):
    """Raised when a frame source cannot be opened or read."""


class BenchFrameSource(Protocol):
    def open(self) -> None:
        ...

    def next_frame(self) -> BenchFrame | None:
        ...

    def release(self) -> None:
        ...
