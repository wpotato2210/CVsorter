from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from coloursorter.deploy import (
    CalibratedOpenCvDetectionConfig,
    CalibratedOpenCvDetectionProvider,
    DetectionError,
    OpenCvDetectionConfig,
    OpenCvDetectionProvider,
    ModelStubDetectionProvider,
    PipelineRunner,
    build_detection_provider,
)
from coloursorter.model import FrameMetadata

FIXTURES = Path(__file__).parent / "fixtures"


def _sample_frame() -> np.ndarray:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[80:160, 40:120] = (200, 200, 255)
    frame[80:160, 180:260] = (200, 255, 200)
    return frame


def _flood_fill_components(binary: np.ndarray) -> list[np.ndarray]:
    visited = np.zeros_like(binary, dtype=bool)
    components: list[np.ndarray] = []
    height, width = binary.shape
    for y in range(height):
        for x in range(width):
            if visited[y, x] or binary[y, x] == 0:
                continue
            stack = [(y, x)]
            points: list[tuple[int, int]] = []
            visited[y, x] = True
            while stack:
                cy, cx = stack.pop()
                points.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and not visited[ny, nx] and binary[ny, nx] > 0:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
            components.append(np.array(points, dtype=np.int32))
    return components


@pytest.fixture(autouse=True)
def _patch_detection_cv2(monkeypatch: pytest.MonkeyPatch) -> None:
    import coloursorter.deploy.detection as detection_module

    def cvt_color(image: np.ndarray, code: int) -> np.ndarray:
        if code == 0:  # BGR2GRAY
            return np.mean(image, axis=2).astype(np.uint8)
        if code == 1:  # BGR2HSV
            hsv = np.zeros_like(image)
            red_mask = (image[..., 2] > image[..., 1] + 30) & (image[..., 2] > image[..., 0] + 30)
            green_mask = (image[..., 1] > image[..., 2] + 30) & (image[..., 1] > image[..., 0] + 30)
            hsv[..., 0][red_mask] = 0
            hsv[..., 0][green_mask] = 60
            hsv[..., 1] = np.max(image, axis=2)
            hsv[..., 2] = np.max(image, axis=2)
            return hsv.astype(np.uint8)
        raise AssertionError(f"unsupported conversion code: {code}")

    def threshold(gray: np.ndarray, threshold_value: int, max_value: int, _mode: int):
        binary = np.where(gray >= threshold_value, max_value, 0).astype(np.uint8)
        return threshold_value, binary

    def find_contours(binary: np.ndarray, _retr: int, _chain: int):
        return _flood_fill_components(binary), None

    def contour_area(contour: np.ndarray) -> float:
        return float(contour.shape[0])

    def moments(contour: np.ndarray) -> dict[str, float]:
        ys = contour[:, 0].astype(np.float64)
        xs = contour[:, 1].astype(np.float64)
        m00 = float(contour.shape[0])
        return {"m00": m00, "m10": float(xs.sum()), "m01": float(ys.sum())}

    def bounding_rect(contour: np.ndarray) -> tuple[int, int, int, int]:
        ys = contour[:, 0]
        xs = contour[:, 1]
        x_min = int(xs.min())
        x_max = int(xs.max())
        y_min = int(ys.min())
        y_max = int(ys.max())
        return x_min, y_min, x_max - x_min + 1, y_max - y_min + 1

    def mean(roi: np.ndarray) -> tuple[float, float, float, float]:
        channel_means = roi.mean(axis=(0, 1))
        return float(channel_means[0]), float(channel_means[1]), float(channel_means[2]), 0.0

    fake_cv2 = SimpleNamespace(
        COLOR_BGR2GRAY=0,
        COLOR_BGR2HSV=1,
        THRESH_BINARY=0,
        RETR_EXTERNAL=0,
        CHAIN_APPROX_SIMPLE=0,
        cvtColor=cvt_color,
        threshold=threshold,
        findContours=find_contours,
        contourArea=contour_area,
        moments=moments,
        boundingRect=bounding_rect,
        mean=mean,
    )
    monkeypatch.setattr(detection_module, "cv2", fake_cv2)


@pytest.mark.parametrize(
    ("provider_name", "expected_type"),
    [
        ("opencv_basic", OpenCvDetectionProvider),
        ("opencv_calibrated", CalibratedOpenCvDetectionProvider),
        ("model_stub", ModelStubDetectionProvider),
    ],
)
def test_provider_selection_returns_expected_implementation(provider_name: str, expected_type: type) -> None:
    provider = build_detection_provider(provider_name)
    assert isinstance(provider, expected_type)


def test_provider_selection_rejects_unknown_provider() -> None:
    with pytest.raises(DetectionError, match="Unsupported detection provider"):
        build_detection_provider("does-not-exist")


@pytest.mark.parametrize(
    "provider",
    [
        OpenCvDetectionProvider(OpenCvDetectionConfig(min_area_px=10, reject_red_threshold=120)),
        CalibratedOpenCvDetectionProvider(
            CalibratedOpenCvDetectionConfig(
                min_area_px=10,
                reject_hue_min=0,
                reject_hue_max=20,
                reject_saturation_min=80,
                reject_value_min=80,
            )
        ),
    ],
)
def test_detection_output_schema_is_pipeline_compatible(provider) -> None:
    detections = provider.detect(_sample_frame())
    assert detections
    for detection in detections:
        assert detection.object_id
        assert detection.classification in {"accept", "reject"}
        assert 0.0 <= detection.infection_score <= 1.0

    runner = PipelineRunner(
        lane_config_path=FIXTURES / "lane_geometry_22.yaml",
        calibration_path=FIXTURES / "calibration_edge_valid.json",
    )
    frame = FrameMetadata(frame_id=10, timestamp_s=0.25, image_height_px=240, image_width_px=320)
    result = runner.run(frame=frame, detections=detections)
    assert len(result.decisions) == len(detections)


def test_detection_fails_fast_for_invalid_frame_shape() -> None:
    provider = OpenCvDetectionProvider()
    with pytest.raises(DetectionError, match="shape"):
        provider.detect(np.zeros((64, 64), dtype=np.uint8))


def test_detection_fails_fast_for_invalid_frame_dtype() -> None:
    provider = OpenCvDetectionProvider()
    with pytest.raises(DetectionError, match="dtype uint8"):
        provider.detect(np.zeros((64, 64, 3), dtype=np.float32))


def test_model_stub_detection_provider_maps_reject_threshold() -> None:
    provider = build_detection_provider("model_stub")
    detections = provider.detect(_sample_frame())
    assert len(detections) == 1
    assert detections[0].classification in {"accept", "reject"}
