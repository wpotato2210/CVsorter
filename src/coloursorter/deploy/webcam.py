from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class WebcamConnectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class WebcamConnection:
    device_index: int
    capture: Any


def _open_capture(device_index: int, api_preference: int | None) -> Any:
    try:
        import cv2  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise WebcamConnectionError("OpenCV is required for webcam autodetection (pip install opencv-python).") from exc

    return cv2.VideoCapture(device_index) if api_preference is None else cv2.VideoCapture(device_index, api_preference)


def autodetect_webcam_index(max_devices: int = 10, api_preference: int | None = None) -> int:
    if max_devices <= 0:
        raise ValueError("max_devices must be > 0")

    for device_index in range(max_devices):
        capture = _open_capture(device_index, api_preference)
        try:
            if capture.isOpened():
                return device_index
        finally:
            capture.release()

    raise WebcamConnectionError(f"No webcam detected in device range [0, {max_devices - 1}].")


def autoconnect_webcam(max_devices: int = 10, api_preference: int | None = None) -> WebcamConnection:
    device_index = autodetect_webcam_index(max_devices=max_devices, api_preference=api_preference)
    capture = _open_capture(device_index, api_preference)
    if not capture.isOpened():
        capture.release()
        raise WebcamConnectionError(f"Webcam {device_index} was detected but could not be connected.")
    return WebcamConnection(device_index=device_index, capture=capture)
