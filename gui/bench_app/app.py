from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from coloursorter.bench import AckCode, BenchLogEntry, FaultState


@dataclass(frozen=True)
class QueueState:
    depth: int
    capacity: int
    state: str


class BenchMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ColourSorter Bench App")
        central = QWidget()
        self.setCentralWidget(central)

        layout = QGridLayout(central)
        layout.addWidget(self._build_live_preview_panel(), 0, 0)
        layout.addWidget(self._build_lane_overlay_panel(), 0, 1)
        layout.addWidget(self._build_queue_panel(), 1, 0)
        layout.addWidget(self._build_controls_panel(), 1, 1)
        layout.addWidget(self._build_fault_panel(), 2, 0, 1, 2)
        layout.addWidget(self._build_log_panel(), 3, 0, 1, 2)

    def _build_live_preview_panel(self) -> QGroupBox:
        box = QGroupBox("Live Frame Preview")
        box_layout = QVBoxLayout(box)
        self.preview_label = QLabel("No frame loaded")
        self.preview_label.setFixedHeight(220)
        self.preview_label.setAlignment(Qt.AlignCenter)
        box_layout.addWidget(self.preview_label)
        return box

    def _build_lane_overlay_panel(self) -> QGroupBox:
        box = QGroupBox("Lane Overlay")
        box_layout = QVBoxLayout(box)
        self.lane_overlay_label = QLabel("Lane boundaries pending")
        box_layout.addWidget(self.lane_overlay_label)
        return box

    def _build_queue_panel(self) -> QGroupBox:
        box = QGroupBox("Queue Depth / State")
        box_layout = QVBoxLayout(box)
        self.queue_depth_label = QLabel("Depth: 0/0")
        self.queue_state_label = QLabel("State: idle")
        box_layout.addWidget(self.queue_depth_label)
        box_layout.addWidget(self.queue_state_label)
        return box

    def _build_controls_panel(self) -> QGroupBox:
        box = QGroupBox("Mode / Homing Controls")
        row = QHBoxLayout(box)
        self.replay_button = QPushButton("Replay mode")
        self.live_button = QPushButton("Live mode")
        self.home_button = QPushButton("Home")
        row.addWidget(self.replay_button)
        row.addWidget(self.live_button)
        row.addWidget(self.home_button)
        return box

    def _build_fault_panel(self) -> QGroupBox:
        box = QGroupBox("Fault Indicators")
        row = QHBoxLayout(box)
        self.safe_label = QLabel("SAFE: off")
        self.watchdog_label = QLabel("WATCHDOG: off")
        row.addWidget(self.safe_label)
        row.addWidget(self.watchdog_label)
        return box

    def _build_log_panel(self) -> QGroupBox:
        box = QGroupBox("Bench Telemetry")
        box_layout = QVBoxLayout(box)
        self.log_table = QTableWidget(0, 6)
        self.log_table.setHorizontalHeaderLabels(
            [
                "Frame Ts (s)",
                "Trigger Ts (s)",
                "Lane/Decision",
                "Rejection",
                "RTT (ms)",
                "ACK",
            ]
        )
        box_layout.addWidget(self.log_table)
        return box

    def update_frame_preview(self, frame_rgb: bytes, width: int, height: int) -> None:
        image = QImage(frame_rgb, width, height, QImage.Format.Format_RGB888)
        self.preview_label.setPixmap(QPixmap.fromImage(image).scaled(self.preview_label.size(), Qt.KeepAspectRatio))

    def set_lane_overlay(self, overlay_text: str) -> None:
        self.lane_overlay_label.setText(overlay_text)

    def set_queue_state(self, queue_state: QueueState) -> None:
        self.queue_depth_label.setText(f"Depth: {queue_state.depth}/{queue_state.capacity}")
        self.queue_state_label.setText(f"State: {queue_state.state}")

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


def run() -> int:
    app = QApplication([])
    window = BenchMainWindow()
    window.resize(1200, 900)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
