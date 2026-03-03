from __future__ import annotations


class MonotonicFrameIdError(ValueError):
    """Raised when frame ids regress or repeat."""


class MonotonicFrameIdPolicy:
    def __init__(self) -> None:
        self._last_frame_id: int | None = None

    @property
    def last_frame_id(self) -> int | None:
        return self._last_frame_id

    def validate(self, frame_id: int) -> None:
        if self._last_frame_id is not None and frame_id <= self._last_frame_id:
            raise MonotonicFrameIdError(
                f"Frame id must increase strictly: last={self._last_frame_id}, incoming={frame_id}"
            )
        self._last_frame_id = frame_id
