from __future__ import annotations

import random
from typing import Protocol

from PySide6.QtCore import QObject, QTimer
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


class POCIntegration(QObject):
    """POC glue: simulated detection -> serial command -> GUI status updates.

    This class is intentionally small and event-loop safe. It uses a QTimer tick
    so the GUI remains responsive while periodically polling frames.
    """

    def __init__(self, controller: BenchController, gui: BenchGUI, tick_ms: int = 100) -> None:
        super().__init__()
        self._controller = controller
        self._gui = gui
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
        frame = self._controller._next_frame()
        if frame is None:
            self._set_status("Waiting for frame...")
            return

        if not self._simple_detection(frame):
            self._set_status(f"Frame {getattr(frame, 'frame_id', '?')}: no detection")
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

        self._set_status(f"Frame {getattr(frame, 'frame_id', '?')}: sent {command}")

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


if __name__ == "__main__":
    # Bench-only runnable demo: no camera required.
    # The controller already falls back to simulated frames when LIVE camera open fails.
    runtime_config = RuntimeConfig.load_startup("configs/bench_runtime.yaml")
    app = QApplication([])
    controller = BenchAppController(app, runtime_config=runtime_config)

    # Keep a `status_label` attribute on the GUI for this integration stub contract.
    if not hasattr(controller.window, "status_label"):
        controller.window.status_label = controller.window.last_command_label

    integration = POCIntegration(controller=controller, gui=controller.window, tick_ms=100)

    # Start a live run and integration once the event loop starts.
    QTimer.singleShot(0, controller.on_live_clicked)
    QTimer.singleShot(0, integration.start)

    raise SystemExit(controller.start())
