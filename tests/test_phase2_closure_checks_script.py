from __future__ import annotations

from pathlib import Path


def test_phase2_closure_script_runs_required_commands() -> None:
    script = Path("scripts/run_phase2_closure_checks.cmd").read_text(encoding="utf-8")

    required_commands = (
        'call :run_check "firmware unit tests" "run_tests.bat"',
        'call :run_check "phase2 task tests" "python -m pytest tests/test_phase2_task*.py"',
        'call :run_check "phase2 reliability gates" "python -m pytest tests/test_phase2_reliability_gate.py tests/test_phase2_lane_segmentation_robustness.py"',
        'call :run_check "host test suite" "python -m pytest tests/"',
        'call :run_check "bench integration tests" "python -m pytest bench/"',
        'call :run_check "coverage generation" "python -m pytest --cov=src/coloursorter --cov-report=xml"',
    )

    for command in required_commands:
        assert command in script


def test_phase2_closure_script_writes_text_report() -> None:
    script = Path("scripts/run_phase2_closure_checks.cmd").read_text(encoding="utf-8")

    assert 'set "REPORT_TXT=%ARTIFACT_ROOT%\\phase2_closure_report_%TIMESTAMP%.txt"' in script
    assert ') > "%REPORT_TXT%"' in script
    assert 'echo What you need next:' in script


def test_phase2_closure_script_keeps_prompt_open_with_report_path() -> None:
    script = Path("scripts/run_phase2_closure_checks.cmd").read_text(encoding="utf-8")

    assert 'echo [phase2-closure] Report saved to: %REPORT_TXT%' in script
    assert 'echo [phase2-closure] Press any key to close this window...' in script
    assert 'pause >nul' in script
