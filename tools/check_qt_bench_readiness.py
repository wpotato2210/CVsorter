#!/usr/bin/env python3
"""Repository Qt/bench readiness validation."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PYSIDE_VALIDATOR = REPO_ROOT / "tools" / "validate_pyside6_modules.py"


def _run(cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, cwd=cwd, env=merged_env, text=True, capture_output=True)


def _extract_missing_system_deps(error_text: str) -> list[str]:
    matches = set(re.findall(r"(lib[^\s:]+\.so(?:\.\d+)*)", error_text))
    return sorted(matches)


def _check_pyproject() -> tuple[bool, str]:
    if not PYPROJECT_PATH.exists():
        return False, "pyproject.toml not found"

    raw = PYPROJECT_PATH.read_text(encoding="utf-8")
    if tomllib is not None:
        try:
            data: dict[str, Any] = tomllib.loads(raw)
        except Exception as exc:
            return False, f"pyproject.toml parse failed: {exc}"
        deps = data.get("project", {}).get("dependencies", [])
        if not isinstance(deps, list):
            return False, "pyproject.toml [project].dependencies is not a list"
        has_pyside = any(isinstance(dep, str) and dep.strip().lower().startswith("pyside6") for dep in deps)
    else:
        project_match = re.search(r"\[project\](.*?)(?:\n\[|\Z)", raw, re.S)
        if not project_match:
            return False, "pyproject.toml missing [project] section"
        has_pyside = bool(re.search(r"^\s*\"?PySide6", project_match.group(1), re.M))
    if not has_pyside:
        return False, "PySide6 dependency missing in [project].dependencies"

    return True, "pyproject.toml valid and PySide6 dependency declared"


def _check_validator_tool() -> tuple[bool, str]:
    if not PYSIDE_VALIDATOR.exists():
        return False, "tools/validate_pyside6_modules.py not found"
    if not os.access(PYSIDE_VALIDATOR, os.X_OK):
        return False, "tools/validate_pyside6_modules.py is not executable"
    return True, "tools/validate_pyside6_modules.py exists and is executable"


def _run_qt_import_check() -> dict[str, Any]:
    script = (
        "import json\n"
        "payload = {'ok': True, 'error': ''}\n"
        "try:\n"
        "    from PySide6 import QtWidgets  # noqa: F401\n"
        "except Exception as exc:\n"
        "    payload['ok'] = False\n"
        "    payload['error'] = repr(exc)\n"
        "print(json.dumps(payload))\n"
    )
    proc = _run([sys.executable, "-I", "-c", script], env={"QT_QPA_PLATFORM": "offscreen"})
    payload: dict[str, Any] = {"ok": False, "error": "", "stderr": proc.stderr}
    if proc.stdout.strip():
        try:
            payload.update(json.loads(proc.stdout.strip().splitlines()[-1]))
        except json.JSONDecodeError:
            payload["ok"] = False
            payload["error"] = f"Non-JSON output: {proc.stdout.strip()}"
    if proc.returncode != 0 and not payload.get("error"):
        payload["error"] = proc.stderr.strip() or f"Python exited with code {proc.returncode}"
    payload["stderr"] = proc.stderr.strip()
    payload["missing_system_deps"] = _extract_missing_system_deps((payload.get("error") or "") + "\n" + payload["stderr"])
    return payload


def _run_qt_smoke_lifecycle() -> dict[str, Any]:
    script = (
        "import json\n"
        "payload = {'ok': True, 'error': ''}\n"
        "try:\n"
        "    from PySide6.QtWidgets import QApplication\n"
        "    app = QApplication([])\n"
        "    app.processEvents()\n"
        "    app.quit()\n"
        "except Exception as exc:\n"
        "    payload['ok'] = False\n"
        "    payload['error'] = repr(exc)\n"
        "print(json.dumps(payload))\n"
    )
    proc = _run([sys.executable, "-I", "-c", script], env={"QT_QPA_PLATFORM": "offscreen"})
    result = {"ok": False, "error": "", "stderr": proc.stderr.strip()}
    if proc.stdout.strip():
        try:
            result.update(json.loads(proc.stdout.strip().splitlines()[-1]))
        except json.JSONDecodeError:
            result["error"] = f"Non-JSON output: {proc.stdout.strip()}"
    if proc.returncode != 0 and not result.get("error"):
        result["error"] = proc.stderr.strip() or f"Python exited with code {proc.returncode}"
    return result


def _detect_tests() -> tuple[bool, str]:
    tests_dir = REPO_ROOT / "tests"
    found = any(tests_dir.glob("test_*.py")) if tests_dir.exists() else False
    if found:
        return True, "Detected unit tests in tests/"

    if PYPROJECT_PATH.exists():
        content = PYPROJECT_PATH.read_text(encoding="utf-8")
        if "[tool.pytest.ini_options]" in content or "pytest" in content:
            return True, "Detected pytest references in pyproject.toml"

    return False, "No unit tests or pytest configuration detected"


def _run_pytest() -> dict[str, Any]:
    proc = _run([sys.executable, "-m", "pytest"], env={"QT_QPA_PLATFORM": "offscreen"})
    summary_line = ""
    combined = f"{proc.stdout}\n{proc.stderr}"
    for line in reversed(combined.splitlines()):
        if re.search(r"\b(\d+\s+passed|\d+\s+failed|no tests ran)\b", line):
            summary_line = line.strip()
            break
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "summary": summary_line or "pytest summary not found",
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _run_validator() -> dict[str, Any]:
    proc = _run([sys.executable, str(PYSIDE_VALIDATOR), "--verbose"], env={"QT_QPA_PLATFORM": "offscreen"})
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> int:
    results: dict[str, Any] = {}

    pyproject_ok, pyproject_msg = _check_pyproject()
    validator_file_ok, validator_file_msg = _check_validator_tool()
    tests_present, tests_msg = _detect_tests()

    qt_import = _run_qt_import_check()
    qt_smoke = _run_qt_smoke_lifecycle()
    validator_run = _run_validator() if PYSIDE_VALIDATOR.exists() else {"ok": False, "returncode": 127, "stdout": "", "stderr": "validator missing"}
    pytest_run = _run_pytest() if tests_present else {"ok": False, "returncode": 5, "summary": "tests not detected", "stdout": "", "stderr": ""}

    results["qt_import"] = qt_import
    results["pyproject"] = {"ok": pyproject_ok, "message": pyproject_msg}
    results["validator_file"] = {"ok": validator_file_ok, "message": validator_file_msg}
    results["validator_run"] = validator_run
    results["qt_smoke"] = qt_smoke
    results["tests_detected"] = {"ok": tests_present, "message": tests_msg}
    results["pytest"] = pytest_run

    print("=== Qt / Bench Readiness Report ===")
    print(f"Qt import readiness: {'PASS' if qt_import.get('ok') else 'FAIL'}")
    if not qt_import.get("ok"):
        print(f"  error: {qt_import.get('error')}")
    if qt_import.get("stderr"):
        print(f"  stderr: {qt_import['stderr']}")

    missing_deps = qt_import.get("missing_system_deps", [])
    print(f"Missing system deps (from errors): {', '.join(missing_deps) if missing_deps else 'none detected'}")

    print(f"pyproject.toml check: {'PASS' if pyproject_ok else 'FAIL'} ({pyproject_msg})")
    print(f"validator tool file check: {'PASS' if validator_file_ok else 'FAIL'} ({validator_file_msg})")
    print(f"validator runtime check: {'PASS' if validator_run.get('ok') else 'FAIL'} (exit={validator_run.get('returncode')})")
    print(f"Qt offscreen smoke lifecycle: {'PASS' if qt_smoke.get('ok') else 'FAIL'}")
    if not qt_smoke.get("ok"):
        print(f"  error: {qt_smoke.get('error')}")
    if qt_smoke.get("stderr"):
        print(f"  stderr: {qt_smoke.get('stderr')}")

    print(f"Unit tests presence: {'PASS' if tests_present else 'FAIL'} ({tests_msg})")
    print(f"pytest run: {'PASS' if pytest_run.get('ok') else 'FAIL'} (exit={pytest_run.get('returncode')})")
    print(f"pytest summary: {pytest_run.get('summary')}")

    failing = [
        not qt_import.get("ok"),
        not pyproject_ok,
        not validator_file_ok,
        not validator_run.get("ok"),
        not qt_smoke.get("ok"),
        not tests_present,
        not pytest_run.get("ok"),
    ]

    print("\n=== JSON Report ===")
    print(json.dumps(results, indent=2))

    return 1 if any(failing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
