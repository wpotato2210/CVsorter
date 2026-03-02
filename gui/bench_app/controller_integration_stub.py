from __future__ import annotations

import random
from typing import Protocol

import cv2
import numpy as np
from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from coloursorter.config import RuntimeConfig

from .controller import BenchAppController


class BenchController(Protocol):
    """Minimal controller surface needed by the POC stub."""

    def _next_frame(self): ...  # noqa: ANN202 - frame type stays flexible for POC usage

    def _send_serial_command(self, cmd: str) -> None: ...


class BenchGUI(Protocol):
    """Minimal GUI surface needed by the POC stub."""

    status_label: QLabel


class OverlayMixin:
    """Frame overlay helper for bench preview labels."""

    _gui: BenchGUI

    def _get_preview_label(self) -> QLabel | None:
        if hasattr(self._gui, "camera_preview_label") and isinstance(self._gui.camera_preview_label, QLabel):
            return self._gui.camera_preview_label
        if hasattr(self._gui, "preview_label") and isinstance(self._gui.preview_label, QLabel):
            self._gui.camera_preview_label = self._gui.preview_label
            return self._gui.camera_preview_label
        if hasattr(self._gui, "status_label") and isinstance(self._gui.status_label, QLabel):
            self._gui.camera_preview_label = QLabel("Waiting for frame...", self._gui.status_label.parentWidget())
            return self._gui.camera_preview_label
        return None

    def show_frame_overlay(self, frame, detected: bool) -> None:
        preview_label = self._get_preview_label()
        if preview_label is None:
            return

        image_bgr = frame if isinstance(frame, np.ndarray) else getattr(frame, "image_bgr", None)
        if not isinstance(image_bgr, np.ndarray) or image_bgr.ndim != 3:
            return

        overlay = image_bgr.copy()
        if detected:
            # Keep this drawing section localized so it can be swapped with real CV boxes later.
            height, width = overlay.shape[:2]
            margin_x = max(20, width // 10)
            margin_y = max(20, height // 10)
            cv2.rectangle(overlay, (margin_x, margin_y), (width - margin_x, height - margin_y), (0, 255, 0), 2)
            cv2.putText(overlay, "DETECTED", (margin_x, margin_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        frame_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        image = QImage(
            frame_rgb.data,
            frame_rgb.shape[1],
            frame_rgb.shape[0],
            frame_rgb.strides[0],
            QImage.Format.Format_RGB888,
        )
        preview_label.setPixmap(QPixmap.fromImage(image).scaled(preview_label.size(), Qt.KeepAspectRatio))


class POCIntegration(QObject, OverlayMixin):
    """POC glue: simulated detection -> serial command -> GUI status updates.

    This class is intentionally small and event-loop safe. It uses a QTimer tick
    so the GUI remains responsive while periodically polling frames.
    """

    def __init__(
        self,
        controller: BenchController,
        gui: BenchGUI,
        tick_ms: int = 100,
        enable_logging: bool = False,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._gui = gui
        self._enable_logging = enable_logging
        self._frame_index = 0
        self.command_log: list[tuple[int, str]] = []
        self._timer = QTimer(self)
        self._timer.setInterval(tick_ms)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        """Start periodic processing ticks."""
        self._timer.start()

    def stop(self) -> None:
        """Stop periodic processing ticks."""
        self._timer.stop()

    def _tick(self) -> None:
        """Advance one integration step without blocking the GUI thread."""
        self._frame_index += 1
        frame = self._controller._next_frame()
        if frame is None:
            self._set_status(f"Frame {self._frame_index}: waiting for frame...")
            return

        detected = self._simple_detection(frame)
        self.show_frame_overlay(frame, detected)

        if not detected:
            self._set_status(f"Frame {self._frame_index}: no detection")
            return

        # For the POC we use a simple textual command; replace with your real
        # protocol payload when integrating with MCU command contracts.
        command = "FIRE_TEST"

        # Prefer the dedicated serial helper if present; otherwise fall back to
        # existing protocol command pathways in BenchAppController.
        if hasattr(self._controller, "_send_serial_command"):
            self._controller._send_serial_command(command)
        elif hasattr(self._controller, "_send_protocol_command"):
            self._controller._send_protocol_command("SCHED", (0, 100))

        servo_feedback = self._mock_servo_feedback()
        self.command_log.append((self._frame_index, command))
        self._set_status(f"Frame {self._frame_index}: sent {command} | {servo_feedback}")

        if self._enable_logging:
            print(f"[POC] frame={self._frame_index} detected=1 cmd={command} {servo_feedback}")

    def _simple_detection(self, frame: object) -> bool:  # noqa: ARG002 - placeholder for future CV
        """POC detection stub: random trigger at ~20% per frame.

        Swap this with your CV detector output threshold check in production.
        """
        return random.random() < 0.20

    def _set_status(self, text: str) -> None:
        if hasattr(self._gui, "status_label") and isinstance(self._gui.status_label, QLabel):
            self._gui.status_label.setText(text)
            return
        if hasattr(self._gui, "last_command_label") and isinstance(self._gui.last_command_label, QLabel):
            self._gui.last_command_label.setText(f"Last command: {text}")
            return

    def _mock_servo_feedback(self) -> str:
        position_deg = random.randint(10, 170)
        duty_pct = random.randint(35, 85)
        return f"servo=OK pos={position_deg}deg duty={duty_pct}%"


if __name__ == "__main__":
    # Bench-only runnable demo: no camera required.
    # The controller already falls back to simulated frames when LIVE camera open fails.
    runtime_config = RuntimeConfig.load_startup("configs/bench_runtime.yaml")
    app = QApplication([])
    controller = BenchAppController(app, runtime_config=runtime_config)

    # Keep a `status_label` attribute on the GUI for this integration stub contract.
    if not hasattr(controller.window, "status_label"):
        controller.window.status_label = controller.window.last_command_label

    integration = POCIntegration(controller=controller, gui=controller.window, tick_ms=100, enable_logging=True)

    # Start a live run and integration once the event loop starts.
    QTimer.singleShot(0, controller.on_live_clicked)
    QTimer.singleShot(0, integration.start)

    raise SystemExit(controller.start())
