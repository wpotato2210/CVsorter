from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QWidget

from coloursorter.bench import AckCode, BenchLogEntry, FaultState
from coloursorter.config import RuntimeConfig

from .load_ui_main_layout import load_ui_main_layout


@dataclass(frozen=True)
class QueueState:
    depth: int
    capacity: int
    controller_state: str
    scheduler_state: str
    mode: str
    degraded_mode: bool = False
    run_state: str = "idle"
    reject_count: int = 0
    ack_fault_count: int = 0
    nack_fault_count: int = 0


class BenchMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._central_widget: QWidget | None = None
        self._ui_root_window: QMainWindow | None = None
        load_ui_main_layout(self)

    def update_frame_preview(self, frame_rgb: bytes, width: int, height: int) -> None:
        image = QImage(frame_rgb, width, height, QImage.Format.Format_RGB888)
        self.preview_label.setPixmap(QPixmap.fromImage(image).scaled(self.preview_label.size(), Qt.KeepAspectRatio))

    def set_lane_overlay(self, overlay_text: str) -> None:
        self.lane_overlay_label.setText(overlay_text)

    def set_queue_state(self, queue_state: QueueState) -> None:
        self.queue_depth_label.setText(f"Depth: {queue_state.depth}/{queue_state.capacity}")
        self.queue_state_label.setText(f"State: {queue_state.controller_state}")
        self.scheduler_state_label.setText(f"Scheduler: {queue_state.scheduler_state}")
        self.mode_label.setText(f"Mode: {queue_state.mode}")
        self.status_label.setText(
            f"Run={queue_state.run_state} | rejects={queue_state.reject_count} | ACK faults={queue_state.ack_fault_count} | NACK faults={queue_state.nack_fault_count}"
        )
        degraded_prefix = "DEGRADED | " if queue_state.degraded_mode else ""
        self.statusBar().showMessage(
            f"{degraded_prefix}{queue_state.controller_state} | mode={queue_state.mode} | sched={queue_state.scheduler_state} | queue={queue_state.depth}/{queue_state.capacity}"
        )

    def set_fault_state(self, fault_state: FaultState) -> None:
        self.safe_label.setText(f"SAFE: {'on' if fault_state == FaultState.SAFE else 'off'}")
        self.watchdog_label.setText(f"WATCHDOG: {'on' if fault_state == FaultState.WATCHDOG else 'off'}")

    def append_log_entry(self, entry: BenchLogEntry) -> None:
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        cells = [
            f"{entry.frame_timestamp_s:.4f}",
            f"{entry.trigger_generation_s:.4f}",
            f"{entry.lane}/{entry.decision}",
            entry.rejection_reason or "-",
            f"{entry.protocol_round_trip_ms:.2f}",
            entry.ack_code.value if isinstance(entry.ack_code, AckCode) else str(entry.ack_code),
        ]
        for index, text in enumerate(cells):
            self.log_table.setItem(row, index, QTableWidgetItem(text))
        if hasattr(self, "log_autoscroll_checkbox") and self.log_autoscroll_checkbox.isChecked():
            self.log_table.scrollToBottom()

    def set_last_command_status(self, message: str) -> None:
        self.last_command_label.setText(f"Last command: {message}")


def main(argv: list[str] | None = None) -> int:
    from .controller import BenchAppController

    parser = argparse.ArgumentParser(description="ColourSorter bench app")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[2] / "configs" / "bench_runtime.yaml"),
        help="Path to runtime YAML config",
    )
    args = parser.parse_args(argv)

    runtime_config = RuntimeConfig.load_startup(args.config)
    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    controller = BenchAppController(app, runtime_config=runtime_config)
    controller.start()
    return app.exec()


def run(argv: list[str] | None = None) -> int:
    return main(argv)


if __name__ == "__main__":
    sys.exit(main())
