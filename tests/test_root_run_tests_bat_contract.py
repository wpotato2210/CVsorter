from __future__ import annotations

from pathlib import Path


def test_root_run_tests_bat_writes_required_report() -> None:
    script = Path("run_tests.bat").read_text(encoding="utf-8")

    assert 'set "REPORT_DIR=test_reports"' in script
    assert 'set "REPORT_FILE=%REPORT_DIR%\\test_results.txt"' in script
    assert 'if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"' in script


def test_root_run_tests_bat_detects_pytest_or_unittest() -> None:
    script = Path("run_tests.bat").read_text(encoding="utf-8")

    assert 'python -c "import pytest"' in script
    assert 'python -m pytest tests/ bench/' in script
    assert 'python -m unittest discover -s tests -p test_*.py -v' in script


def test_root_run_tests_bat_prints_progress_and_summary() -> None:
    script = Path("run_tests.bat").read_text(encoding="utf-8")

    assert 'echo [harness] Checking Python availability...' in script
    assert 'echo [harness] Detecting pytest...' in script
    assert 'echo [harness] PASS: all tests completed successfully.' in script
    assert 'echo [harness] FAIL: one or more checks failed.' in script



def test_readme_documents_run_tests_bat_as_windows_only() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "run_tests.bat" in readme
    assert "Windows-only harness" in readme
    assert "Linux/macOS hosts" in readme


def test_ci_workflow_has_windows_harness_guard_note() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Guard Windows-only run_tests.bat execution on Linux hosts" in workflow
    assert "Linux CI runners execute pytest directly" in workflow
