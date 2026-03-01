from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
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
from coloursorter.config import RuntimeConfig


@dataclass(frozen=True)
class QueueState:
    depth: int
    capacity: int
    controller_state: str
    scheduler_state: str
    mode: str


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
        layout.addWidget(self._build_poc_panel(), 2, 0, 1, 2)
        layout.addWidget(self._build_fault_panel(), 3, 0, 1, 2)
        layout.addWidget(self._build_log_panel(), 4, 0, 1, 2)
        self.statusBar().showMessage("Bench idle")

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
        self.scheduler_state_label = QLabel("Scheduler: IDLE")
        self.mode_label = QLabel("Mode: AUTO")
        box_layout.addWidget(self.queue_depth_label)
        box_layout.addWidget(self.queue_state_label)
        box_layout.addWidget(self.scheduler_state_label)
        box_layout.addWidget(self.mode_label)
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

    def _build_poc_panel(self) -> QGroupBox:
        box = QGroupBox("POC Vertical Slice")
        layout = QGridLayout(box)

        self.serial_connect_button = QPushButton("Serial Connect")
        self.serial_disconnect_button = QPushButton("Serial Disconnect")
        self.fire_test_button = QPushButton("FIRE TEST")
        self.serial_status_label = QLabel("Serial: disconnected")

        self.trigger_threshold_input = QDoubleSpinBox()
        self.trigger_threshold_input.setRange(0.0, 1.0)
        self.trigger_threshold_input.setSingleStep(0.05)
        self.trigger_threshold_input.setValue(0.5)
        self.trigger_threshold_input.setDecimals(2)

        self.belt_speed_input = QDoubleSpinBox()
        self.belt_speed_input.setRange(1.0, 5000.0)
        self.belt_speed_input.setSingleStep(10.0)
        self.belt_speed_input.setValue(140.0)
        self.belt_speed_input.setDecimals(1)

        self.last_command_label = QLabel("Last command: -")

        layout.addWidget(self.serial_connect_button, 0, 0)
        layout.addWidget(self.serial_disconnect_button, 0, 1)
        layout.addWidget(self.fire_test_button, 0, 2)
        layout.addWidget(self.serial_status_label, 0, 3)
        layout.addWidget(QLabel("Trigger threshold"), 1, 0)
        layout.addWidget(self.trigger_threshold_input, 1, 1)
        layout.addWidget(QLabel("belt_speed_mm_s"), 1, 2)
        layout.addWidget(self.belt_speed_input, 1, 3)
        layout.addWidget(self.last_command_label, 2, 0, 1, 4)
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
        self.queue_state_label.setText(f"State: {queue_state.controller_state}")
        self.scheduler_state_label.setText(f"Scheduler: {queue_state.scheduler_state}")
        self.mode_label.setText(f"Mode: {queue_state.mode}")
        self.statusBar().showMessage(
            f"{queue_state.controller_state} | mode={queue_state.mode} | sched={queue_state.scheduler_state} | queue={queue_state.depth}/{queue_state.capacity}"
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

    def set_last_command_status(self, message: str) -> None:
        self.last_command_label.setText(f"Last command: {message}")


def run(argv: list[str] | None = None) -> int:
    from .controller import BenchAppController

    parser = argparse.ArgumentParser(description="ColourSorter bench app")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[2] / "configs" / "bench_runtime.yaml"),
        help="Path to runtime YAML config",
    )
    args = parser.parse_args(argv)

    runtime_config = RuntimeConfig.load_startup(args.config)
    app = QApplication([])
    controller = BenchAppController(app, runtime_config=runtime_config)
    return controller.start()


if __name__ == "__main__":
    raise SystemExit(run())
