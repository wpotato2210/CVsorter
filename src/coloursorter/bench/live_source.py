from __future__ import annotations

from dataclasses import dataclass

import cv2

from .frame_source import FrameSourceError
from .types import BenchFrame


@dataclass(frozen=True)
class LiveConfig:
    camera_index: int
    frame_period_s: float


class LiveFrameSource:
    def __init__(self, config: LiveConfig) -> None:
        self._config = config
        self._capture: cv2.VideoCapture | None = None
        self._frame_id = 0

    def open(self) -> None:
        self.release()
        self._capture = cv2.VideoCapture(self._config.camera_index)
        if not self._capture.isOpened():
            self.release()
            raise FrameSourceError(f"Unable to open camera index {self._config.camera_index}")
        self._frame_id = 0

    def next_frame(self) -> BenchFrame | None:
        if self._capture is None:
            raise FrameSourceError("Live source is not open")

        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise FrameSourceError(f"Unable to read frame from camera index {self._config.camera_index}")

        frame = BenchFrame(
            frame_id=self._frame_id,
            timestamp_s=self._frame_id * self._config.frame_period_s,
            image_bgr=frame,
        )
        self._frame_id += 1
        return frame

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
