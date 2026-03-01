from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2

from .frame_source import FrameSourceError
from .types import BenchFrame


@dataclass(frozen=True)
class ReplayConfig:
    frame_period_s: float


class ReplayFrameSource:
    def __init__(self, source_path: str | Path, config: ReplayConfig) -> None:
        self._source_path = Path(source_path)
        self._config = config
        self._frames_iter: Iterator[BenchFrame] | None = None

    def open(self) -> None:
        self._frames_iter = self._build_frame_iterator()

    def next_frame(self) -> BenchFrame | None:
        if self._frames_iter is None:
            raise FrameSourceError("Replay source is not open")
        return next(self._frames_iter, None)

    def release(self) -> None:
        self._frames_iter = None

    def _build_frame_iterator(self) -> Iterator[BenchFrame]:
        if self._source_path.is_dir():
            return self._frames_from_directory()
        if self._source_path.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}:
            return self._frames_from_video()
        image = cv2.imread(str(self._source_path))
        if image is None:
            raise FrameSourceError(f"Unsupported replay source: {self._source_path}")
        return iter((BenchFrame(frame_id=0, timestamp_s=0.0, image_bgr=image),))

    def _frames_from_directory(self) -> Iterator[BenchFrame]:
        image_paths = sorted(
            path for path in self._source_path.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
        )
        for frame_id, image_path in enumerate(image_paths):
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            yield BenchFrame(
                frame_id=frame_id,
                timestamp_s=frame_id * self._config.frame_period_s,
                image_bgr=image,
            )

    def _frames_from_video(self) -> Iterator[BenchFrame]:
        capture = cv2.VideoCapture(str(self._source_path))
        if not capture.isOpened():
            raise FrameSourceError(f"Unable to open replay video: {self._source_path}")

        frame_id = 0
        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_period_s = 1.0 / fps if fps > 0 else self._config.frame_period_s
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                yield BenchFrame(
                    frame_id=frame_id,
                    timestamp_s=frame_id * frame_period_s,
                    image_bgr=frame,
                )
                frame_id += 1
        finally:
            capture.release()
