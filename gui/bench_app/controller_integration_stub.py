from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class BenchController(Protocol):
    """Minimal controller surface needed by the POC stub."""

    def _next_frame(self) -> np.ndarray | None: ...

    def _send_serial_command(self, cmd: str) -> None: ...


class BenchGUI(Protocol):
    """Minimal GUI surface needed by the POC stub."""

    status_label: QLabel
    camera_preview_label: QLabel


class OverlayMixin:
    """Frame overlay helper for preview labels."""

    _gui: BenchGUI

    def show_frame_overlay(self, frame: np.ndarray, detected: bool) -> None:
        if not isinstance(frame, np.ndarray) or frame.ndim != 3:
            return

        overlay = frame.copy()
        indicator_text = "DETECTED" if detected else "SEARCHING"
        indicator_color = (0, 255, 0) if detected else (0, 165, 255)

        cv2.putText(
            overlay,
            indicator_text,
            (16, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            indicator_color,
            2,
        )

        if detected:
            # Placeholder overlay box/text; replace with model-provided bounding boxes later.
            height, width = overlay.shape[:2]
            margin_x = max(20, width // 8)
            margin_y = max(20, height // 8)
            cv2.rectangle(overlay, (margin_x, margin_y), (width - margin_x, height - margin_y), (0, 255, 0), 2)

        rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self._gui.camera_preview_label.setPixmap(
            pixmap.scaled(self._gui.camera_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )


@dataclass
class CameraConfig:
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480


class POCIntegration(QObject, OverlayMixin):
    """QTimer-driven integration stub with webcam + simulated fallback."""

    def __init__(
        self,
        controller: BenchController,
        gui: BenchGUI,
        tick_ms: int = 100,
        camera_index: int = 0,
        enable_logging: bool = False,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._gui = gui
        self.enable_logging = enable_logging

        self._frame_index: int = 0
        self.last_frame_index: int = 0
        self.last_command: str = ""
        self.command_log: list[str] = []

        self._camera_config = CameraConfig(camera_index=camera_index)
        self._capture: cv2.VideoCapture | None = None
        self._simulated_frame_id = 0

        self._timer = QTimer(self)
        self._timer.setInterval(tick_ms)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._set_status("POC start")
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._set_status("POC stopped")

    def _next_frame(self) -> np.ndarray:
        """Return a webcam frame (BGR) or a simulated fallback frame (BGR)."""
        if self._capture is None:
            capture = cv2.VideoCapture(self._camera_config.camera_index)
            if capture.isOpened():
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._camera_config.frame_width)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._camera_config.frame_height)
                self._capture = capture
            else:
                capture.release()

        if self._capture is not None:
            ok, frame = self._capture.read()
            if ok and isinstance(frame, np.ndarray):
                return frame

        return self._build_simulated_frame()

    def _build_simulated_frame(self) -> np.ndarray:
        height, width = self._camera_config.frame_height, self._camera_config.frame_width
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        x = 40 + (self._simulated_frame_id * 12) % (width - 80)
        cv2.circle(frame, (x, height // 2), 28, (0, 255, 255), -1)
        self._simulated_frame_id += 1
        return frame

    def _tick(self) -> None:
        self._frame_index += 1
        self.last_frame_index = self._frame_index
        frame = self._next_frame()
        detected = self._simple_detection(frame)
        self.show_frame_overlay(frame, detected)

        if not detected:
            self._set_status(f"[{self._frame_index}] detection=none")
            return

        cmd = "FIRE_TEST"
        self.last_command = cmd
        self._controller._send_serial_command(cmd)

        # Replace with parsed MCU ACK + telemetry packet handling when available.
        telemetry = self._mock_servo_feedback(cmd)
        entry = f"[{self._frame_index}] detection=hit cmd={cmd} feedback={telemetry}"
        self.command_log.append(entry)
        self._set_status(entry)

        if self.enable_logging:
            print(entry)

    def _simple_detection(self, frame: np.ndarray) -> bool:
        """
        Placeholder CV bean detection using HSV threshold + contour area.
        Returns True if any contour passes minimal area threshold.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_hsv = np.array([20, 100, 100])
        upper_hsv = np.array([30, 255, 255])
        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = 100
        for cnt in contours:
            if cv2.contourArea(cnt) >= min_area:
                return True
        return False

    def _mock_servo_feedback(self, cmd: str) -> str:
        pos = random.randint(15, 165)
        duty = random.randint(35, 90)
        latency_ms = random.randint(12, 65)
        return f"servo=OK cmd={cmd} pos={pos}deg duty={duty}% latency={latency_ms}ms"

    def _set_status(self, text: str) -> None:
        self._gui.status_label.setText(text)


class DemoController:
    """Bench-only demo controller with minimal serial command handler."""

    def __init__(self) -> None:
        self.sent_commands: list[str] = []

    def _next_frame(self) -> np.ndarray | None:
        return None

    def _send_serial_command(self, cmd: str) -> None:
        # Replace with actual serial transport (USB/UART) in hardware integration.
        self.sent_commands.append(cmd)


class DemoWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("POC Integration Stub")

        self.status_label = QLabel("Idle")
        self.camera_preview_label = QLabel("Waiting for frame")
        self.camera_preview_label.setMinimumSize(640, 480)
        self.camera_preview_label.setAlignment(Qt.AlignCenter)
        self.camera_preview_label.setStyleSheet("background: #101010; color: #d0d0d0;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.camera_preview_label)
        layout.addWidget(self.status_label)


if __name__ == "__main__":
    app = QApplication([])

    window = DemoWindow()
    controller = DemoController()
    integration = POCIntegration(
        controller=controller,
        gui=window,
        tick_ms=100,
        camera_index=0,
        enable_logging=True,
    )

    window.show()
    QTimer.singleShot(0, integration.start)
    app.aboutToQuit.connect(integration.stop)

    # Bench-only mode: if no webcam opens, simulated frames are used automatically.
    raise SystemExit(app.exec())
