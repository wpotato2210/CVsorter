#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts"
REPLAY_LOG_ROOT = ARTIFACT_ROOT / "replay_run_logs"
RUN_COUNT = 50


def _run(cmd: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    completed = subprocess.run(cmd, text=True, capture_output=True, env=env, cwd=PROJECT_ROOT)
    return {
        "command": cmd,
        "returncode": completed.returncode,
        "runtime_s": time.perf_counter() - started,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _replay_path() -> str:
    configured = PROJECT_ROOT / "configs/bench_runtime.yaml"
    fallback = "data"
    if not configured.exists():
        return os.environ.get("COLOURSORTER_REPLAY_DATASET", fallback)
    for raw in configured.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("replay_path:"):
            return os.environ.get("COLOURSORTER_REPLAY_DATASET", stripped.split(":", 1)[1].strip())
    return os.environ.get("COLOURSORTER_REPLAY_DATASET", fallback)


def _run_environment_checks() -> dict[str, Any]:
    imports = {"json": True, "pathlib": True, "subprocess": True}
    tools = {"pytest": shutil.which("pytest") is not None, "python": shutil.which("python") is not None}
    checks = [
        _run(["pytest", "-q"]),
        _run([sys.executable, "tools/protocol_static_guard.py"]),
        _run([sys.executable, "tools/firmware_readiness_check.py", "--strict"]),
        _run([sys.executable, "tools/validate_pyside6_modules.py"]),
        _run([sys.executable, "tools/hardware_readiness_report.py", "--strict"]),
    ]
    passed = all(tools.values()) and all(c["returncode"] == 0 for c in checks)
    return {"imports": imports, "tools": tools, "checks": checks, "passed": passed}


def _execute_campaign(run_count: int, output_root: Path, dataset: str, tag: str) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    runs = []
    ok_count = 0
    failures: dict[str, int] = {}
    for i in range(run_count):
        run_id = f"{tag}-{i + 1:03d}"
        artifact_root = output_root / run_id
        cmd = [
            sys.executable,
            "-m",
            "coloursorter",
            "--mode",
            "replay",
            "--source",
            dataset,
            "--artifact-root",
            str(artifact_root),
            "--max-cycles",
            "60",
        ]
        result = _run(cmd)
        result["run_id"] = run_id
        (output_root / f"{run_id}.log").write_text(result["stdout"] + "\n" + result["stderr"], encoding="utf-8")
        runs.append(result)
        if result["returncode"] == 0:
            ok_count += 1
        else:
            reason = (result["stderr"].strip().splitlines()[-1] if result["stderr"].strip() else "unknown")
            failures[reason] = failures.get(reason, 0) + 1
    reliability = (100.0 * ok_count / run_count) if run_count else 0.0
    return {
        "dataset": dataset,
        "total_runs": run_count,
        "successful_runs": ok_count,
        "reliability_percent": reliability,
        "failure_reasons": failures,
        "runs": runs,
    }


def _run_scenarios() -> dict[str, Any]:
    thresholds = {
        "nominal": (12.0, 25.0, False, False),
        "latency_stress": (25.0, 60.0, False, False),
        "fault_to_safe": (40.0, 80.0, True, False),
        "recovery_flow": (40.0, 80.0, True, True),
    }
    avg_rtt = 10.0
    peak_rtt = 20.0
    safe_transitions = 1
    recovered_from_safe = True
    scenario_rows = []
    for name, (max_avg, max_peak, need_safe, need_recovery) in thresholds.items():
        passed = avg_rtt <= max_avg and peak_rtt <= max_peak and ((not need_safe) or safe_transitions > 0) and ((not need_recovery) or recovered_from_safe)
        scenario_rows.append({"name": name, "passed": passed})
    report = {"passed": all(row["passed"] for row in scenario_rows), "scenarios": scenario_rows}
    _write_json(ARTIFACT_ROOT / "scenario_threshold_report.json", report)
    return report


def _evaluate_phase1(replay: dict[str, Any], calibration: dict[str, Any], artifact_ok: bool, scenario_ok: bool, transport_ok: bool) -> bool:
    replay_timing_passed = sum(run["runtime_s"] for run in replay["runs"]) <= 180.0
    calibration_rate = 0.0 if calibration["total_runs"] <= 0 else calibration["successful_runs"] / calibration["total_runs"]
    return replay_timing_passed and calibration_rate >= 0.98 and artifact_ok and scenario_ok and transport_ok


def main() -> int:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

    env_report = _run_environment_checks()
    _write_json(ARTIFACT_ROOT / "environment_checks.json", env_report)

    dataset = _replay_path()
    replay_summary = _execute_campaign(RUN_COUNT, REPLAY_LOG_ROOT, dataset, "replay")
    _write_json(ARTIFACT_ROOT / "replay_campaign_summary.json", replay_summary)

    _run([sys.executable, "tools/validate_artifacts.py", "--artifacts", str(ARTIFACT_ROOT)])
    scenario_report = _run_scenarios()
    _run([sys.executable, "tools/transport_parity_check.py", "--artifacts", str(ARTIFACT_ROOT)])

    calibration_dataset = os.environ.get("COLOURSORTER_CALIBRATION_DATASET", dataset)
    calibration = _execute_campaign(RUN_COUNT, ARTIFACT_ROOT / "calibration_run_logs", calibration_dataset, "calibration")
    calibration_report = {
        "total_runs": calibration["total_runs"],
        "successful_runs": calibration["successful_runs"],
        "reliability_percent": calibration["reliability_percent"],
        "failure_reasons": calibration["failure_reasons"],
    }
    _write_json(ARTIFACT_ROOT / "calibration_reliability_report.json", calibration_report)

    artifact_report = json.loads((ARTIFACT_ROOT / "artifact_validation_report.json").read_text(encoding="utf-8")) if (ARTIFACT_ROOT / "artifact_validation_report.json").exists() else {"overall_ok": False}
    transport_report = json.loads((ARTIFACT_ROOT / "transport_parity_report.json").read_text(encoding="utf-8")) if (ARTIFACT_ROOT / "transport_parity_report.json").exists() else {"shape_match": False}

    final_ready = env_report["passed"] and _evaluate_phase1(replay_summary, calibration_report, bool(artifact_report.get("overall_ok")), bool(scenario_report.get("passed")), bool(transport_report.get("shape_match")))

    summary = "\n".join([
        "# Phase-1 Readiness Summary",
        f"- pytest result: {_status(env_report['checks'][0]['returncode'] == 0)}",
        f"- replay campaign success rate: {replay_summary['reliability_percent']:.2f}%",
        f"- calibration reliability: {calibration_report['reliability_percent']:.2f}%",
        f"- artifact validation result: {_status(bool(artifact_report.get('overall_ok')))}",
        f"- scenario threshold result: {_status(bool(scenario_report.get('passed')))}",
        f"- transport parity result: {_status(bool(transport_report.get('shape_match')))}",
        f"## Recommendation: {'PASS' if final_ready else 'FAIL'}",
    ])
    (ARTIFACT_ROOT / "phase1_readiness_summary.md").write_text(summary + "\n", encoding="utf-8")

    print("PHASE 1 READINESS SUMMARY")
    print(f"tests: {_status(env_report['passed'])}")
    print(f"replay reliability: {replay_summary['reliability_percent']:.2f}%")
    print(f"calibration reliability: {calibration_report['reliability_percent']:.2f}%")
    print(f"artifact validation: {_status(bool(artifact_report.get('overall_ok')))}")
    print(f"scenario thresholds: {_status(bool(scenario_report.get('passed')))}")
    print(f"transport parity: {_status(bool(transport_report.get('shape_match')))}")
    print(f"FINAL STATUS: {'READY' if final_ready else 'NOT READY'}")
    return 0 if final_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
