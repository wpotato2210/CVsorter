from __future__ import annotations

import random
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtWidgets import QApplication

from coloursorter.config import RuntimeConfig
from gui.bench_app.controller import BenchAppController


class POCIntegration(QObject):
    """POC tick loop that wires simulated detection to serial command + GUI updates.

    This class is intentionally small and event-loop safe. Replace
    ``_simple_detection`` with real CV logic later.
    """

    def __init__(self, controller: BenchAppController, gui: QObject, tick_ms: int = 100) -> None:
        super().__init__()
        self._controller = controller
        self._gui = gui
        self._timer = QTimer(self)
        self._timer.setInterval(tick_ms)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()

    @Slot()
    def _tick(self) -> None:
        frame = self._controller._next_frame()
        if frame is None:
            return

        if not self._simple_detection(frame.image_bgr):
            return

        # Replace this command format with your real scheduler/protocol payload.
        command = "SCHED|0|100"
        ack = self._controller._send_serial_command(command)
        ack_status = "no response" if ack is None else ack.status

        # This scaffold uses `last_command_label`; if a dedicated `status_label`
        # is added later, this fallback keeps the POC runnable either way.
        status_label = getattr(self._gui, "status_label", None)
        if status_label is not None and hasattr(status_label, "setText"):
            status_label.setText(f"POC sent: {command} -> {ack_status}")

        if hasattr(self._gui, "set_last_command_status"):
            self._gui.set_last_command_status(f"{command} -> {ack_status}")

    def _simple_detection(self, frame) -> bool:
        """20% random trigger placeholder for real detection logic."""
        _ = frame
        return random.random() < 0.20


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    runtime_config = RuntimeConfig.load_startup(str(project_root / "configs" / "bench_runtime.yaml"))

    app = QApplication([])
    controller = BenchAppController(app, runtime_config=runtime_config)

    # Ensure this runs in bench-only mode even when no camera is available.
    controller._use_simulated_live_feed = True

    integration = POCIntegration(controller=controller, gui=controller.window, tick_ms=100)
    integration.start()

    controller.window.resize(1200, 900)
    controller.window.show()
    raise SystemExit(app.exec())
