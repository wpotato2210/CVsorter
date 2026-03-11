"""YOLOv8 detection provider for Phase One CVsorter integration.

Module: yolo_provider.YOLOProvider
Inputs:
- frame: (H, W, 3) image array, uint8, BGR or RGB
Outputs:
- predict: list[dict] where each item has
  - bbox: [x1, y1, x2, y2] pixel coordinates
  - class: string class label/id
  - confidence: float in [0, 1]
- predict_with_meta: {"frame_id": Any, "detections": list[dict]}
Side effects:
- loads YOLOv8 model weights from disk during initialization
Dependencies:
- ultralytics
- numpy
Update rate:
- per frame
Norm:
- passthrough image values expected by ultralytics runtime
Device:
- configurable cpu/cuda
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


class YOLOProvider:
    """YOLOv8-backed detection provider with a model_stub-compatible output schema."""

    def __init__(self, model_path: str, device: str = "cpu") -> None:
        self.model_path: str = str(model_path)
        self.device: str = str(device)
        self._model: Any | None = None
        self._degraded: bool = False
        self._degraded_reason: str | None = None

        try:
            from ultralytics import YOLO  # type: ignore[import-untyped]
        except ImportError as exc:
            self._set_degraded(reason="import_failure")
            logger.warning(
                "yolo_provider degraded mode enabled: stage=import model_path=%s device=%s error=%s",
                self.model_path,
                self.device,
                exc,
            )
            return

        try:
            self._model = YOLO(self.model_path)
            self._model.to(self.device)
        except (FileNotFoundError, OSError, RuntimeError, ValueError, TypeError) as exc:
            self._set_degraded(reason="runtime_failure")
            logger.error(
                "yolo_provider degraded mode enabled: stage=runtime model_path=%s device=%s error=%s",
                self.model_path,
                self.device,
                exc,
            )
            self._model = None

    @property
    def degraded(self) -> bool:
        return self._degraded

    @property
    def degraded_reason(self) -> str | None:
        return self._degraded_reason

    def _set_degraded(self, reason: str) -> None:
        self._degraded = True
        self._degraded_reason = reason

    def predict(self, frame: np.ndarray) -> list[dict[str, Any]]:
        """Run YOLO inference on one frame and return pipeline-safe detection dictionaries."""
        if self._model is None:
            return []
        if not isinstance(frame, np.ndarray):
            return []
        if frame.ndim != 3 or frame.shape[2] != 3:
            return []

        try:
            results = self._model(frame, verbose=False)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            self._set_degraded(reason="inference_failure")
            logger.error(
                "yolo_provider inference failure: stage=inference model_path=%s device=%s error=%s",
                self.model_path,
                self.device,
                exc,
            )
            return []

        if not results:
            return []

        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        names: Any = getattr(result, "names", {})
        detections: list[dict[str, Any]] = []

        for box in boxes:
            try:
                xyxy_raw = box.xyxy[0].tolist()
                bbox = [float(xyxy_raw[0]), float(xyxy_raw[1]), float(xyxy_raw[2]), float(xyxy_raw[3])]

                cls_idx = int(float(box.cls[0]))
                if isinstance(names, dict):
                    class_label = str(names.get(cls_idx, cls_idx))
                elif isinstance(names, list) and 0 <= cls_idx < len(names):
                    class_label = str(names[cls_idx])
                else:
                    class_label = str(cls_idx)

                confidence = float(box.conf[0])
                if confidence < 0.0:
                    confidence = 0.0
                if confidence > 1.0:
                    confidence = 1.0

                detections.append({"bbox": bbox, "class": class_label, "confidence": confidence})
            except Exception:
                continue

        return detections

    def predict_with_meta(self, frame: np.ndarray, frame_id: Any = None) -> dict[str, Any]:
        """Run detection and include a passthrough frame identifier."""
        return {"frame_id": frame_id, "detections": self.predict(frame)}
