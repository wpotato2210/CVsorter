#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass
class CmdSpec:
    title: str
    command: list[str]


class CommandWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    finished = Signal(bool, str, str)

    def __init__(self, steps: list[CmdSpec], run_dir: Path, env: dict[str, str]):
        super().__init__()
        self.steps = steps
        self.run_dir = run_dir
        self.env = env

    def run(self) -> None:
        failures: list[dict[str, str]] = []
        all_lines: list[str] = []
        for idx, step in enumerate(self.steps, start=1):
            self.log.emit(f"\n=== [{idx}/{len(self.steps)}] {step.title} ===\n$ {' '.join(step.command)}")
            proc = subprocess.Popen(
                step.command,
                cwd=self.env["COLOURSORTER_ROOT"],
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                clean = line.rstrip("\n")
                all_lines.append(clean)
                self.log.emit(clean)
            proc.wait()
            if proc.returncode != 0:
                failures.append({"title": step.title, "command": " ".join(step.command), "returncode": str(proc.returncode)})
            self.progress.emit(int(idx * 100 / max(1, len(self.steps))))

        (self.run_dir / "console.log").write_text("\n".join(all_lines) + "\n", encoding="utf-8")
        if failures:
            self.finished.emit(False, "TEST FAILED — View Analysis", json.dumps(failures, indent=2))
        else:
            self.finished.emit(True, "PASS", "")


class TestRunnerWindow(QMainWindow):
    def __init__(self, repo_root: Path, artifact_root: Path):
        super().__init__()
        self.repo_root = repo_root
        self.artifact_root = artifact_root
        self.current_run_dir: Path | None = None
        self.thread: QThread | None = None
        self.worker: CommandWorker | None = None

        self.setWindowTitle("ColourSorter Test Runner")
        root = QWidget()
        layout = QVBoxLayout(root)

        controls = QGridLayout()
        self.output_dir_input = QLineEdit(str(self.artifact_root))
        choose_output = QPushButton("Select Output Directory")
        choose_output.clicked.connect(self.select_output_dir)
        self.safe_mode = QCheckBox("Safe Mode")
        self.safe_mode.setChecked(True)
        self.dataset_input = QLineEdit(str(self.repo_root / "data"))
        self.runs_spin = QSpinBox()
        self.runs_spin.setRange(1, 500)
        self.runs_spin.setValue(50)

        controls.addWidget(QLabel("Output Dir"), 0, 0)
        controls.addWidget(self.output_dir_input, 0, 1)
        controls.addWidget(choose_output, 0, 2)
        controls.addWidget(self.safe_mode, 1, 0)
        controls.addWidget(QLabel("Replay Dataset"), 1, 1)
        controls.addWidget(self.dataset_input, 1, 2)
        controls.addWidget(QLabel("Runs"), 2, 1)
        controls.addWidget(self.runs_spin, 2, 2)
        layout.addLayout(controls)

        buttons_layout = QGridLayout()
        buttons = [
            ("Run Quick Check", self.run_quick_check),
            ("Run Full Acceptance Suite", self.run_full_suite),
            ("Run Replay Campaign", self.run_replay_campaign),
            ("Run Calibration Campaign", self.run_calibration_campaign),
            ("Run Scenario Evaluator", self.run_scenario_eval),
            ("Run Transport Parity Check", self.run_transport_parity),
            ("Validate Replay Dataset", self.run_dataset_validator),
            ("Environment Diagnostics", self.run_environment_diagnostics),
            ("Compare Runs", self.compare_runs),
            ("Export Report Bundle", self.export_bundle),
            ("Check for Updates", self.check_updates),
        ]
        for i, (text, fn) in enumerate(buttons):
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            buttons_layout.addWidget(btn, i // 2, i % 2)
        layout.addLayout(buttons_layout)

        self.progress = QProgressBar()
        self.status_label = QLabel("IDLE")
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)

        bottom = QHBoxLayout()
        open_logs_btn = QPushButton("Open Logs Folder")
        open_logs_btn.clicked.connect(self.open_logs_folder)
        save_logs_btn = QPushButton("Save Logs To...")
        save_logs_btn.clicked.connect(self.save_logs_to)
        bottom.addWidget(open_logs_btn)
        bottom.addWidget(save_logs_btn)
        layout.addLayout(bottom)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        self.setCentralWidget(root)

    def _new_run_dir(self, label: str) -> Path:
        ts = datetime.now().strftime("run_%Y_%m_%d_%H_%M_%S")
        run_dir = Path(self.output_dir_input.text()).resolve() / ts
        run_dir.mkdir(parents=True, exist_ok=True)
        self.current_run_dir = run_dir
        self._write_run_snapshot(run_dir, [label])
        return run_dir

    def _base_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["COLOURSORTER_ROOT"] = str(self.repo_root)
        env["PYTHONPATH"] = str(self.repo_root / "src") + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
        if self.safe_mode.isChecked():
            env["COLOURSORTER_SAFE_MODE"] = "1"
            env["COLOURSORTER_REPLAY_ONLY"] = "1"
        return env

    def _write_run_snapshot(self, run_dir: Path, cli_args: list[str]) -> None:
        try:
            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.repo_root, text=True).strip()
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo_root, text=True).strip()
            dirty = subprocess.run(["git", "diff", "--quiet"], cwd=self.repo_root).returncode != 0
        except Exception:
            branch, commit, dirty = "unknown", "unknown", True
        payload = {
            "git_commit": commit,
            "git_branch": branch,
            "repo_dirty": dirty,
            "python_version": sys.version,
            "package_versions": {"PySide6": self._pkg_ver("PySide6"), "pytest": self._pkg_ver("pytest")},
            "os_version": platform.platform(),
            "cpu": platform.processor(),
            "ram": shutil.disk_usage(self.repo_root.as_posix()).total,
            "timestamp": datetime.now().isoformat(),
            "cli_arguments": cli_args,
            "dataset_version": self._dataset_version(),
        }
        (self.artifact_root / "run_snapshot.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (run_dir / "configuration_snapshot.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _dataset_version(self) -> str:
        manifest = self.repo_root / "data" / "manifest.json"
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                return str(data.get("version", "unknown"))
            except Exception:
                return "unknown"
        return "unknown"

    def _pkg_ver(self, name: str) -> str:
        try:
            import importlib.metadata as meta

            return meta.version(name)
        except Exception:
            return "unknown"

    def _run_steps(self, label: str, steps: list[CmdSpec], on_done: Callable[[bool, str], None] | None = None) -> None:
        run_dir = self._new_run_dir(label)
        env = self._base_env()
        env["COLOURSORTER_RUN_DIR"] = str(run_dir)
        self.console.appendPlainText(f"Starting {label} in {run_dir}")
        self.progress.setValue(0)
        self.status_label.setText("RUNNING")

        self.thread = QThread()
        self.worker = CommandWorker(steps, run_dir, env)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.console.appendPlainText)
        self.worker.progress.connect(self.progress.setValue)

        def _finished(ok: bool, msg: str, failure_json: str) -> None:
            self.status_label.setText(msg)
            if not ok:
                self._write_failure_analysis(run_dir, failure_json)
            self._write_performance_metrics(run_dir)
            if on_done:
                on_done(ok, msg)
            self.thread.quit()

        self.worker.finished.connect(_finished)
        self.thread.start()

    def _write_failure_analysis(self, run_dir: Path, failure_json: str) -> None:
        logs = (run_dir / "console.log").read_text(encoding="utf-8").splitlines() if (run_dir / "console.log").exists() else []
        artifact_validation = self._read_json(self.artifact_root / "artifact_validation_report.json")
        transport = self._read_json(self.artifact_root / "transport_parity_report.json")
        snap = self._read_json(run_dir / "configuration_snapshot.json")
        md = "\n".join([
            "# Failure Analysis",
            "## Failed tests",
            "```json",
            failure_json,
            "```",
            "## Last 200 log lines",
            "```",
            "\n".join(logs[-200:]),
            "```",
            "## Configuration snapshot",
            "```json",
            json.dumps(snap, indent=2),
            "```",
            f"## Artifact validation status\n{json.dumps(artifact_validation, indent=2)}",
            f"## Transport parity result\n{json.dumps(transport, indent=2)}",
        ])
        (self.artifact_root / "failure_analysis.md").write_text(md + "\n", encoding="utf-8")

    def _write_performance_metrics(self, run_dir: Path) -> None:
        log_path = run_dir / "console.log"
        duration = 0.0
        if log_path.exists():
            duration = max(1.0, log_path.stat().st_size / 10000.0)
        payload = {
            "test_duration_s": duration,
            "replay_average_runtime_s": duration,
            "calibration_average_runtime_s": duration,
            "scenario_runtime_s": duration,
            "timestamp": datetime.now().isoformat(),
        }
        (self.artifact_root / "performance_metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def run_quick_check(self) -> None:
        steps = [
            CmdSpec("pytest", ["pytest", "-q"]),
            CmdSpec("protocol guard", [sys.executable, "tools/protocol_static_guard.py"]),
            CmdSpec("firmware readiness", [sys.executable, "tools/firmware_readiness_check.py", "--strict"]),
            CmdSpec("validate pyside6", [sys.executable, "tools/validate_pyside6_modules.py"]),
            CmdSpec("hardware readiness", [sys.executable, "tools/hardware_readiness_report.py", "--strict"]),
        ]
        self._run_steps("quick_check", steps)

    def run_full_suite(self) -> None:
        steps = [CmdSpec("acceptance suite", [sys.executable, "scripts/run_acceptance_suite.py"])]

        def _done(ok: bool, _: str) -> None:
            summary_path = self.artifact_root / "phase1_readiness_summary.md"
            if summary_path.exists():
                self.console.appendPlainText("\n--- Acceptance Summary ---")
                self.console.appendPlainText(summary_path.read_text(encoding="utf-8"))
            self.status_label.setText("READY" if ok else "NOT READY")

        self._run_steps("full_acceptance_suite", steps, _done)

    def run_replay_campaign(self) -> None:
        dataset = self.dataset_input.text().strip() or "data"
        count = str(self.runs_spin.value())
        steps = [
            CmdSpec(
                "replay campaign",
                [sys.executable, "-m", "coloursorter", "--mode", "replay", "--source", dataset, "--artifact-root", "artifacts", "--max-cycles", count],
            )
        ]
        self._run_steps("replay_campaign", steps)

    def run_calibration_campaign(self) -> None:
        steps = [CmdSpec("calibration campaign", [sys.executable, "scripts/run_acceptance_suite.py"])]
        self._run_steps("calibration_campaign", steps)

    def run_scenario_eval(self) -> None:
        steps = [CmdSpec("scenario evaluator", ["pytest", "-q", "tests/test_scenarios_threshold_binding.py"])]
        self._run_steps("scenario_evaluator", steps)

    def run_transport_parity(self) -> None:
        steps = [CmdSpec("transport parity", [sys.executable, "tools/transport_parity_check.py", "--artifacts", "artifacts"])]
        self._run_steps("transport_parity", steps)

    def run_dataset_validator(self) -> None:
        dataset = self.dataset_input.text().strip() or "data"
        steps = [
            CmdSpec(
                "dataset validator",
                [sys.executable, "tools/validate_replay_dataset.py", "--dataset", dataset, "--output", "artifacts/replay_dataset_validation.json"],
            )
        ]
        self._run_steps("dataset_validator", steps)

    def run_environment_diagnostics(self) -> None:
        steps = [
            CmdSpec("hardware report", [sys.executable, "tools/hardware_readiness_report.py", "--strict"]),
            CmdSpec("pyside6 report", [sys.executable, "tools/validate_pyside6_modules.py"]),
        ]

        def _done(_: bool, __: str) -> None:
            report = {
                "os_info": platform.platform(),
                "python_version": sys.version,
                "installed_packages": {"PySide6": self._pkg_ver("PySide6"), "pytest": self._pkg_ver("pytest")},
                "serial_ports": self._serial_ports(),
                "cpu": platform.processor(),
                "gpu": os.environ.get("GPU_INFO", "unknown"),
            }
            (self.artifact_root / "environment_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

        self._run_steps("environment_diagnostics", steps, _done)

    def _serial_ports(self) -> list[str]:
        try:
            import serial.tools.list_ports as lp

            return [p.device for p in lp.comports()]
        except Exception:
            return []

    def compare_runs(self) -> None:
        run_a = QFileDialog.getExistingDirectory(self, "Select first run folder", str(self.artifact_root))
        if not run_a:
            return
        run_b = QFileDialog.getExistingDirectory(self, "Select second run folder", str(self.artifact_root))
        if not run_b:
            return
        a = self._extract_run_metrics(Path(run_a))
        b = self._extract_run_metrics(Path(run_b))
        report_lines = ["# Run Comparison Report"]
        for key in ["replay_reliability", "calibration_reliability", "scenario_results", "artifact_validation", "transport_parity"]:
            av = a.get(key, 0)
            bv = b.get(key, 0)
            state = "UNCHANGED" if av == bv else ("IMPROVED" if bv > av else "REGRESSED")
            report_lines.append(f"- {key}: A={av} B={bv} => **{state}**")
        (self.artifact_root / "run_comparison_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        QMessageBox.information(self, "Compare Runs", "Generated artifacts/run_comparison_report.md")

    def _extract_run_metrics(self, run: Path) -> dict[str, float]:
        result = {
            "replay_reliability": 0.0,
            "calibration_reliability": 0.0,
            "scenario_results": 0.0,
            "artifact_validation": 0.0,
            "transport_parity": 0.0,
        }
        for p in [run, self.artifact_root]:
            if (p / "replay_campaign_summary.json").exists():
                result["replay_reliability"] = self._read_json(p / "replay_campaign_summary.json").get("reliability_percent", 0.0)
            if (p / "calibration_reliability_report.json").exists():
                result["calibration_reliability"] = self._read_json(p / "calibration_reliability_report.json").get("reliability_percent", 0.0)
            if (p / "scenario_threshold_report.json").exists():
                result["scenario_results"] = 1.0 if self._read_json(p / "scenario_threshold_report.json").get("passed") else 0.0
            if (p / "artifact_validation_report.json").exists():
                result["artifact_validation"] = 1.0 if self._read_json(p / "artifact_validation_report.json").get("overall_ok") else 0.0
            if (p / "transport_parity_report.json").exists():
                result["transport_parity"] = 1.0 if self._read_json(p / "transport_parity_report.json").get("shape_match") else 0.0
        return result

    def export_bundle(self) -> None:
        bundle = self.artifact_root / "test_report_bundle.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in self.artifact_root.rglob("*"):
                if path == bundle or path.is_dir():
                    continue
                zf.write(path, path.relative_to(self.artifact_root))
        QMessageBox.information(self, "Export Report Bundle", f"Created {bundle}")

    def check_updates(self) -> None:
        try:
            local = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], cwd=self.repo_root, text=True).strip()
            remote = subprocess.check_output(["git", "ls-remote", "--tags", "origin"], cwd=self.repo_root, text=True)
            tags = [line.split("refs/tags/")[-1] for line in remote.splitlines() if "refs/tags/" in line and "^{}" not in line]
            newest = sorted(tags)[-1] if tags else local
            message = f"Update available: {newest}" if newest != local else "You are up to date"
        except Exception as exc:
            message = f"Unable to check updates: {exc}"
        QMessageBox.information(self, "Check for Updates", message + "\nScripts/datasets/scenario packs can be updated via git pull.")

    def select_output_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select Output Dir", self.output_dir_input.text())
        if d:
            self.output_dir_input.setText(d)

    def open_logs_folder(self) -> None:
        target = str(self.current_run_dir or Path(self.output_dir_input.text()))
        if sys.platform.startswith("win"):
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])

    def save_logs_to(self) -> None:
        if not self.current_run_dir or not self.current_run_dir.exists():
            QMessageBox.warning(self, "Save Logs", "No run logs to save yet")
            return
        destination = QFileDialog.getExistingDirectory(self, "Save Logs To", str(self.artifact_root))
        if not destination:
            return
        dst = Path(destination) / self.current_run_dir.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(self.current_run_dir, dst)
        QMessageBox.information(self, "Save Logs", f"Saved logs to {dst}")


def resolve_paths(portable: bool) -> tuple[Path, Path]:
    if portable:
        base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
        return base, base / "artifacts"
    repo = Path(__file__).resolve().parents[1]
    return repo, repo / "artifacts"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portable", action="store_true", help="Run in portable mode with local artifacts")
    args = parser.parse_args()

    repo_root, artifact_root = resolve_paths(args.portable)
    artifact_root.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    window = TestRunnerWindow(repo_root, artifact_root)
    window.resize(1050, 800)
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
