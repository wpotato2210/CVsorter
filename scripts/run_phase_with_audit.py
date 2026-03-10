#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


def _iso8601_utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 64), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AuditLogger:
    def __init__(
        self,
        log_path: Path,
        run_id: str,
        operator_id: str | None,
        software_version: dict[str, str],
        hardware_snapshot: dict[str, Any],
    ) -> None:
        self._log_path = log_path
        self._run_id = run_id
        self._operator_id = operator_id
        self._software_version = software_version
        self._hardware_snapshot = hardware_snapshot
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event_type: str, fields: dict[str, Any]) -> None:
        entry: dict[str, Any] = {
            "run_id": self._run_id,
            "timestamp": _iso8601_utc_now(),
            "operator_id": self._operator_id,
            "software_version": self._software_version,
            "hardware_snapshot": self._hardware_snapshot,
            "event": event_type,
        }
        entry.update(fields)
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def validate_log_completeness(log_path: Path, run_id: str) -> tuple[bool, list[str]]:
    required_order = [
        "run_start",
        "recipe_selection",
        "threshold_binding",
        "calibration_binding",
        "operator_action",
        "run_end",
    ]
    entries: list[dict[str, Any]] = []
    if not log_path.exists():
        return False, [f"missing log file: {log_path}"]

    with log_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            payload = json.loads(raw)
            if payload.get("run_id") == run_id:
                entries.append(payload)

    errors: list[str] = []
    if not entries:
        return False, [f"no entries for run_id={run_id}"]

    for index, event in enumerate(required_order):
        found = next((i for i, item in enumerate(entries) if item.get("event") == event), -1)
        if found < 0:
            errors.append(f"missing required event: {event}")
            continue
        if index > 0:
            prior = next((i for i, item in enumerate(entries) if item.get("event") == required_order[index - 1]), -1)
            if prior >= 0 and found < prior:
                errors.append(f"event out of order: {event}")

    return len(errors) == 0, errors


def _parse_key_value(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"Expected key=value pair, got: {raw}")
        key, value = raw.split("=", 1)
        if not key:
            raise ValueError(f"Empty key in: {raw}")
        result[key] = value
    return result


def _default_software_version(module_name: str, run_script: str) -> dict[str, str]:
    script_path = Path(run_script)
    if script_path.exists():
        return {module_name: _sha256_file(script_path)}
    return {module_name: "unknown"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap Phase-N run scripts with deterministic JSONL audit logging.")
    parser.add_argument("--phase", default="phase1", help="Phase label used in output file names (e.g., phase1, phase2).")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--run-mode", choices=["operator", "replay", "test"], default="operator")
    parser.add_argument("--test-batch-id", required=True)
    parser.add_argument("--camera-recipe", required=True)
    parser.add_argument("--lighting-recipe", required=True)
    parser.add_argument("--detector-provider", required=True)
    parser.add_argument("--detector-threshold", required=True)
    parser.add_argument("--calibration-path", required=True)
    parser.add_argument("--lane-config-path", required=True)
    parser.add_argument("--camera-id", default="unknown")
    parser.add_argument("--light-id", default="unknown")
    parser.add_argument("--sensor-status", default="unknown")
    parser.add_argument("--status-on-success", choices=["success", "partial", "fail"], default="success")
    parser.add_argument("--status-on-failure", choices=["success", "partial", "fail"], default="fail")
    parser.add_argument("--software-version", action="append", default=[], help="Repeatable module=version_hash")
    parser.add_argument("--hardware-extra", action="append", default=[], help="Repeatable key=value for future hardware fields")
    parser.add_argument("--summary-metric", action="append", default=[], help="Repeatable key=value summary metric")
    parser.add_argument("--run-script", default="scripts/run_acceptance_suite.py")
    parser.add_argument("passthrough", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    calibration_path = Path(args.calibration_path)
    lane_config_path = Path(args.lane_config_path)
    if not calibration_path.exists() or not lane_config_path.exists():
        missing = [str(path) for path in [calibration_path, lane_config_path] if not path.exists()]
        raise FileNotFoundError(f"missing required calibration inputs: {missing}")

    software_version = _parse_key_value(args.software_version) if args.software_version else _default_software_version("phase_runner", args.run_script)
    hardware_snapshot: dict[str, Any] = {
        "camera_id": args.camera_id,
        "light_id": args.light_id,
        "sensor_status": args.sensor_status,
        "run_mode": args.run_mode,
    }
    hardware_snapshot.update(_parse_key_value(args.hardware_extra))

    log_path = Path(f"audit_log_{args.phase}.jsonl")
    logger = AuditLogger(log_path, args.run_id, args.operator_id, software_version, hardware_snapshot)

    logger.emit("run_start", {"test_batch_id": args.test_batch_id})
    logger.emit("recipe_selection", {"camera_recipe": args.camera_recipe, "lighting_recipe": args.lighting_recipe})
    logger.emit("threshold_binding", {"detector_provider": args.detector_provider, "detector_threshold": args.detector_threshold})
    logger.emit(
        "calibration_binding",
        {
            "calibration_path": str(calibration_path),
            "calibration_hash": _sha256_file(calibration_path),
            "lane_config_path": str(lane_config_path),
            "lane_config_hash": _sha256_file(lane_config_path),
        },
    )

    logger.emit("operator_action", {"action": "run_started"})

    passthrough_args = args.passthrough if args.passthrough is not None else []
    if passthrough_args and passthrough_args[0] == "--":
        passthrough_args = passthrough_args[1:]
    command = [sys.executable, args.run_script, *passthrough_args]
    completed = subprocess.run(command, text=True)

    if completed.returncode != 0:
        logger.emit(
            "error_warning",
            {
                "error_code": "RUN_SCRIPT_EXIT_NONZERO",
                "message": f"run script exited with code {completed.returncode}",
                "severity": "critical",
            },
        )

    logger.emit(
        "parameter_change",
        {
            "parameter_name": "run_mode",
            "old_value": "uninitialized",
            "new_value": args.run_mode,
        },
    )
    logger.emit("operator_action", {"action": "run_stopped"})

    default_summary = {
        "replay_reliability": "unknown",
        "calibration_reliability": "unknown",
        "artifact_validation": "unknown",
        "scenario_thresholds": "unknown",
        "transport_parity": "unknown",
    }
    default_summary.update(_parse_key_value(args.summary_metric))
    logger.emit(
        "run_end",
        {
            "status": args.status_on_success if completed.returncode == 0 else args.status_on_failure,
            "summary_metrics": default_summary,
            "exit_code": completed.returncode,
        },
    )

    valid, errors = validate_log_completeness(log_path, args.run_id)
    if not valid:
        logger.emit(
            "error_warning",
            {
                "error_code": "AUDIT_LOG_INCOMPLETE",
                "message": "; ".join(errors),
                "severity": "critical",
            },
        )
        return 2
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
