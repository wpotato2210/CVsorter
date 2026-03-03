from __future__ import annotations

from collections import deque


class FirmwareSerialRxBuffer:
    def __init__(self, capacity: int = 256) -> None:
        self.capacity = capacity
        self._buffer: deque[str] = deque()
        self._frames: deque[str] = deque()
        self.overflow_count = 0

    def push_byte(self, value: str) -> None:
        if len(value) != 1:
            raise ValueError("value must be exactly one character")
        if len(self._buffer) >= self.capacity:
            self.overflow_count += 1
            return
        self._buffer.append(value)
        if value == "\n":
            frame = "".join(self._buffer).strip()
            self._frames.append(frame)
            self._buffer.clear()

    def push_stream(self, payload: str) -> None:
        for byte in payload:
            self.push_byte(byte)

    def pop_frame(self) -> str | None:
        if not self._frames:
            return None
        return self._frames.popleft()
