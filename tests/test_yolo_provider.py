from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from yolo_provider import YOLOProvider


class _FakeBox:
    def __init__(self, xyxy: list[float], cls_idx: int, conf: float) -> None:
        self.xyxy = np.array([xyxy], dtype=np.float32)
        self.cls = np.array([cls_idx], dtype=np.float32)
        self.conf = np.array([conf], dtype=np.float32)


class _FakeResult:
    def __init__(self, boxes: list[_FakeBox], names: dict[int, str] | None = None) -> None:
        self.boxes = boxes
        self.names = names or {}


class _FakeModel:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.device = "cpu"

    def to(self, device: str) -> None:
        self.device = device

    def __call__(self, _frame: np.ndarray, verbose: bool = False) -> list[_FakeResult]:
        assert verbose is False
        return [_FakeResult([_FakeBox([1, 2, 3, 4], 0, 0.9)], names={0: "bean"})]


def test_yolo_provider_predict_returns_expected_schema(monkeypatch) -> None:
    import types
    import sys

    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=_FakeModel))
    provider = YOLOProvider(model_path="weights/yolov8s.pt", device="cpu")

    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    detections = provider.predict(frame)

    assert len(detections) == 1
    assert detections[0]["bbox"] == [1.0, 2.0, 3.0, 4.0]
    assert detections[0]["class"] == "bean"
    assert detections[0]["confidence"] == pytest.approx(0.9)


def test_yolo_provider_predict_with_meta_passthrough(monkeypatch) -> None:
    import types
    import sys

    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=_FakeModel))
    provider = YOLOProvider(model_path="weights/yolov8s.pt", device="cpu")

    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    payload = provider.predict_with_meta(frame, frame_id=7)

    assert payload["frame_id"] == 7
    assert isinstance(payload["detections"], list)


def test_yolo_provider_returns_empty_list_on_inference_failure(monkeypatch) -> None:
    class _FailingModel(_FakeModel):
        def __call__(self, _frame: np.ndarray, verbose: bool = False) -> list[_FakeResult]:
            raise RuntimeError("inference failure")

    import types
    import sys

    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=_FailingModel))
    provider = YOLOProvider(model_path="weights/yolov8s.pt", device="cpu")

    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    assert provider.predict(frame) == []
