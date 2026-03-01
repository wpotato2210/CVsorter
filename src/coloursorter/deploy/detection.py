from __future__ import annotations

from dataclasses import dataclass

import cv2

from coloursorter.model import ObjectDetection


class DetectionProvider:
    def detect(self, frame_bgr: object) -> list[ObjectDetection]:
        raise NotImplementedError


@dataclass(frozen=True)
class OpenCvDetectionConfig:
    min_area_px: int = 120
    reject_red_threshold: int = 140


class OpenCvDetectionProvider(DetectionProvider):
    def __init__(self, config: OpenCvDetectionConfig | None = None) -> None:
        self._config = config or OpenCvDetectionConfig()

    def detect(self, frame_bgr: object) -> list[ObjectDetection]:
        if frame_bgr is None:
            return []

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
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
            roi = frame_bgr[y : y + h, x : x + w]
            mean_bgr = cv2.mean(roi)
            classification = "reject" if mean_bgr[2] >= self._config.reject_red_threshold else "accept"

            detections.append(
                ObjectDetection(
                    object_id=f"det-{index}",
                    centroid_x_px=centroid_x,
                    centroid_y_px=centroid_y,
                    classification=classification,
                )
            )

        return sorted(detections, key=lambda item: item.object_id)
