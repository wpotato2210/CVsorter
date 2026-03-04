from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json
from typing import Callable

import cv2
import numpy as np

from coloursorter.model import ObjectDetection

DETECTION_PROVIDER_VALUES = ("opencv_basic", "opencv_calibrated", "model_stub")
DETECTION_LABEL_VALUES = ("accept", "reject")


class DetectionError(ValueError):
    """Raised when detection cannot execute due to invalid frame or provider configuration."""


class DetectionProvider(ABC):
    """Provider contract for deploy-time object detection.

    Input frame contract:
    - frame_bgr must be a numpy ndarray with shape (height, width, 3)
    - channel order must be BGR, uint8 values in [0, 255]

    Output contract:
    - returns list[ObjectDetection]
    - object_id must be unique per frame
    - centroid_x_px and centroid_y_px must be finite pixel coordinates
    - classification must be one of DETECTION_LABEL_VALUES
    - infection_score is interpreted as classification confidence in [0.0, 1.0]
    """

    @abstractmethod
    def detect(self, frame_bgr: object) -> list[ObjectDetection]:
        raise NotImplementedError

    @property
    def provider_version(self) -> str:
        return "unknown"

    @property
    def model_version(self) -> str:
        return "n/a"

    @property
    def active_config_hash(self) -> str:
        return ""

    @property
    def last_validation_metrics(self) -> dict[str, float | bool]:
        return {}


@dataclass(frozen=True)
class PreprocessConfig:
    enable_normalization: bool = True
    target_luma: float = 128.0
    gray_world_strength: float = 0.6


def _stable_config_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_frame(frame_bgr: np.ndarray, config: PreprocessConfig) -> tuple[np.ndarray, dict[str, float | bool]]:
    frame = frame_bgr.astype(np.float32)
    luma_before = float(np.mean(frame))
    if not config.enable_normalization:
        return frame_bgr, {
            "preprocess_valid": True,
            "luma_before": luma_before,
            "luma_after": luma_before,
            "exposure_gain": 1.0,
            "wb_gain_b": 1.0,
            "wb_gain_g": 1.0,
            "wb_gain_r": 1.0,
            "clipped_ratio": 0.0,
        }

    exposure_gain = max(0.25, min(4.0, config.target_luma / max(luma_before, 1.0)))
    adjusted = frame * exposure_gain

    channel_means = adjusted.mean(axis=(0, 1))
    mean_gray = float(np.mean(channel_means))
    wb_gains = np.ones(3, dtype=np.float32)
    if mean_gray > 0:
        ideal = mean_gray / np.maximum(channel_means, 1.0)
        wb_gains = (1.0 - config.gray_world_strength) + (ideal * config.gray_world_strength)
    adjusted *= wb_gains.reshape((1, 1, 3))

    clipped_ratio = float(np.mean((adjusted > 255.0) | (adjusted < 0.0)))
    normalized = np.clip(adjusted, 0.0, 255.0).astype(np.uint8)
    luma_after = float(np.mean(normalized))
    preprocess_valid = bool(np.isfinite(luma_after) and clipped_ratio <= 0.2)
    return normalized, {
        "preprocess_valid": preprocess_valid,
        "luma_before": luma_before,
        "luma_after": luma_after,
        "exposure_gain": float(exposure_gain),
        "wb_gain_b": float(wb_gains[0]),
        "wb_gain_g": float(wb_gains[1]),
        "wb_gain_r": float(wb_gains[2]),
        "clipped_ratio": clipped_ratio,
    }


@dataclass(frozen=True)
class OpenCvDetectionConfig:
    min_area_px: int = 120
    reject_red_threshold: int = 140


@dataclass(frozen=True)
class CalibratedOpenCvDetectionConfig:
    min_area_px: int = 120
    reject_hue_min: int = 0
    reject_hue_max: int = 12
    reject_saturation_min: int = 90
    reject_value_min: int = 90


def _validate_frame(frame_bgr: object) -> np.ndarray:
    if frame_bgr is None:
        raise DetectionError("frame_bgr is required")
    if not isinstance(frame_bgr, np.ndarray):
        raise DetectionError("frame_bgr must be a numpy.ndarray")
    if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        raise DetectionError("frame_bgr must have shape (height, width, 3)")
    if frame_bgr.dtype != np.uint8:
        raise DetectionError("frame_bgr must have dtype uint8")
    return frame_bgr


def _validate_detection_output(detections: list[ObjectDetection]) -> list[ObjectDetection]:
    seen_ids: set[str] = set()
    for detection in detections:
        if detection.object_id in seen_ids:
            raise DetectionError(f"duplicate object_id: {detection.object_id}")
        seen_ids.add(detection.object_id)
        if detection.classification not in DETECTION_LABEL_VALUES:
            raise DetectionError(
                f"classification must be one of {DETECTION_LABEL_VALUES}; got {detection.classification!r}"
            )
        if not (0.0 <= detection.infection_score <= 1.0):
            raise DetectionError("infection_score must be within [0.0, 1.0]")
    return detections


class OpenCvDetectionProvider(DetectionProvider):
    def __init__(self, config: OpenCvDetectionConfig | None = None, preprocess_config: PreprocessConfig | None = None) -> None:
        self._config = config or OpenCvDetectionConfig()
        self._preprocess_config = preprocess_config or PreprocessConfig()
        self._last_validation_metrics: dict[str, float | bool] = {}
        self._active_config_hash = _stable_config_hash(
            {
                "provider": "opencv_basic",
                "min_area_px": self._config.min_area_px,
                "reject_red_threshold": self._config.reject_red_threshold,
                "preprocess": self._preprocess_config.__dict__,
            }
        )

    def detect(self, frame_bgr: object) -> list[ObjectDetection]:
        frame = _validate_frame(frame_bgr)
        frame, self._last_validation_metrics = _normalize_frame(frame, self._preprocess_config)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections: list[ObjectDetection] = []
        for index, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < self._config.min_area_px:
                continue

            moments = cv2.moments(contour)
            if moments["m00"] <= 0:
                continue
            centroid_x = float(moments["m10"] / moments["m00"])
            centroid_y = float(moments["m01"] / moments["m00"])

            x, y, w, h = cv2.boundingRect(contour)
            roi = frame[y : y + h, x : x + w]
            mean_bgr = cv2.mean(roi)
            red_level = float(mean_bgr[2])
            classification = "reject" if red_level >= self._config.reject_red_threshold else "accept"
            confidence = min(1.0, abs(red_level - self._config.reject_red_threshold) / 255.0)

            detections.append(
                ObjectDetection(
                    object_id=f"det-{index}",
                    centroid_x_px=centroid_x,
                    centroid_y_px=centroid_y,
                    classification=classification,
                    infection_score=confidence,
                )
            )

        return _validate_detection_output(sorted(detections, key=lambda item: item.object_id))

    @property
    def provider_version(self) -> str:
        return "opencv_basic@2"

    @property
    def active_config_hash(self) -> str:
        return self._active_config_hash

    @property
    def last_validation_metrics(self) -> dict[str, float | bool]:
        return dict(self._last_validation_metrics)


class CalibratedOpenCvDetectionProvider(DetectionProvider):
    def __init__(self, config: CalibratedOpenCvDetectionConfig | None = None, preprocess_config: PreprocessConfig | None = None) -> None:
        self._config = config or CalibratedOpenCvDetectionConfig()
        self._preprocess_config = preprocess_config or PreprocessConfig()
        self._last_validation_metrics: dict[str, float | bool] = {}
        self._active_config_hash = _stable_config_hash(
            {
                "provider": "opencv_calibrated",
                "min_area_px": self._config.min_area_px,
                "reject_hue_min": self._config.reject_hue_min,
                "reject_hue_max": self._config.reject_hue_max,
                "reject_saturation_min": self._config.reject_saturation_min,
                "reject_value_min": self._config.reject_value_min,
                "preprocess": self._preprocess_config.__dict__,
            }
        )

    def detect(self, frame_bgr: object) -> list[ObjectDetection]:
        frame = _validate_frame(frame_bgr)
        frame, self._last_validation_metrics = _normalize_frame(frame, self._preprocess_config)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        detections: list[ObjectDetection] = []
        for index, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < self._config.min_area_px:
                continue

            moments = cv2.moments(contour)
            if moments["m00"] <= 0:
                continue

            centroid_x = float(moments["m10"] / moments["m00"])
            centroid_y = float(moments["m01"] / moments["m00"])

            x, y, w, h = cv2.boundingRect(contour)
            hsv_roi = hsv[y : y + h, x : x + w]
            mean_hsv = cv2.mean(hsv_roi)
            mean_hue = float(mean_hsv[0])
            mean_sat = float(mean_hsv[1])
            mean_val = float(mean_hsv[2])

            is_reject = (
                self._config.reject_hue_min <= mean_hue <= self._config.reject_hue_max
                and mean_sat >= self._config.reject_saturation_min
                and mean_val >= self._config.reject_value_min
            )
            classification = "reject" if is_reject else "accept"
            hue_range = max(1.0, float(self._config.reject_hue_max - self._config.reject_hue_min + 1))
            hue_center = (self._config.reject_hue_min + self._config.reject_hue_max) / 2.0
            hue_confidence = max(0.0, 1.0 - abs(mean_hue - hue_center) / hue_range)
            sat_confidence = min(1.0, mean_sat / 255.0)
            val_confidence = min(1.0, mean_val / 255.0)
            confidence = max(0.0, min(1.0, 0.5 * hue_confidence + 0.25 * sat_confidence + 0.25 * val_confidence))

            detections.append(
                ObjectDetection(
                    object_id=f"det-{index}",
                    centroid_x_px=centroid_x,
                    centroid_y_px=centroid_y,
                    classification=classification,
                    infection_score=confidence,
                )
            )

        return _validate_detection_output(sorted(detections, key=lambda item: item.object_id))

    @property
    def provider_version(self) -> str:
        return "opencv_calibrated@2"

    @property
    def active_config_hash(self) -> str:
        return self._active_config_hash

    @property
    def last_validation_metrics(self) -> dict[str, float | bool]:
        return dict(self._last_validation_metrics)


@dataclass(frozen=True)
class ModelStubDetectionConfig:
    reject_threshold: float = 0.5


class ModelStubDetectionProvider(DetectionProvider):
    """Simple model-adapter provider for baseline wiring tests.

    The adapter expects a callable with signature `predict(frame_bgr) -> list[dict]`
    where each dict contains object_id, centroid_x_px, centroid_y_px, label, confidence.
    """

    def __init__(self, predictor: Callable[[np.ndarray], list[dict[str, float | str]]] | None = None, config: ModelStubDetectionConfig | None = None) -> None:
        self._config = config or ModelStubDetectionConfig()
        self._predictor = predictor or self._default_predictor
        self._active_config_hash = _stable_config_hash(
            {
                "provider": "model_stub",
                "reject_threshold": self._config.reject_threshold,
            }
        )

    @staticmethod
    def _default_predictor(frame_bgr: np.ndarray) -> list[dict[str, float | str]]:
        height, width = frame_bgr.shape[:2]
        if height == 0 or width == 0:
            return []
        return [
            {
                "object_id": "det-0",
                "centroid_x_px": float(width / 2.0),
                "centroid_y_px": float(height / 2.0),
                "label": "accept",
                "confidence": 0.51,
            }
        ]

    def detect(self, frame_bgr: object) -> list[ObjectDetection]:
        frame = _validate_frame(frame_bgr)
        raw = self._predictor(frame)
        detections: list[ObjectDetection] = []
        for index, item in enumerate(raw):
            confidence = float(item.get("confidence", 0.0))
            label = str(item.get("label", "accept"))
            classification = "reject" if (label == "reject" and confidence >= self._config.reject_threshold) else "accept"
            detections.append(
                ObjectDetection(
                    object_id=str(item.get("object_id", f"det-{index}")),
                    centroid_x_px=float(item.get("centroid_x_px", 0.0)),
                    centroid_y_px=float(item.get("centroid_y_px", 0.0)),
                    classification=classification,
                    infection_score=max(0.0, min(1.0, confidence)),
                )
            )
        return _validate_detection_output(detections)

    @property
    def provider_version(self) -> str:
        return "model_stub@1"

    @property
    def model_version(self) -> str:
        return "model_stub_baseline"

    @property
    def active_config_hash(self) -> str:
        return self._active_config_hash


def build_detection_provider(
    provider_name: str,
    basic_config: OpenCvDetectionConfig | None = None,
    calibrated_config: CalibratedOpenCvDetectionConfig | None = None,
    model_stub_config: ModelStubDetectionConfig | None = None,
    preprocess_config: PreprocessConfig | None = None,
) -> DetectionProvider:
    if provider_name == "opencv_basic":
        return OpenCvDetectionProvider(config=basic_config, preprocess_config=preprocess_config)
    if provider_name == "opencv_calibrated":
        return CalibratedOpenCvDetectionProvider(config=calibrated_config, preprocess_config=preprocess_config)
    if provider_name == "model_stub":
        return ModelStubDetectionProvider(config=model_stub_config)
    raise DetectionError(f"Unsupported detection provider: {provider_name}")
