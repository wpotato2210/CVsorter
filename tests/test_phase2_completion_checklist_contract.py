from __future__ import annotations

from pathlib import Path


def test_phase2_completion_checklist_tracks_required_workstreams() -> None:
    checklist = Path("docs/phase2_completion_tasks.md").read_text(encoding="utf-8")

    required_sections = (
        "Workstream A — Bench/Live behavioral parity (HIGH)",
        "A1. Pass runtime thresholds and fault context through bench runner",
        "A2. Enforce startup diagnostics as a hard gate in live runtime",
        "Workstream B — Timebase and boundary contract integrity (MEDIUM)",
        "B1. Use real monotonic timestamps for live frame capture",
        "B2. Tighten ingest channel contract to BGR `(H,W,3)` or add explicit conversion",
        "Workstream C — Interface explicitness and production-safety hardening (MEDIUM)",
        "C1. Remove monkey-patched runtime threshold dependency",
        "C2. Prevent accidental `model_stub` use in integration/live modes",
    )

    for section in required_sections:
        assert section in checklist


def test_phase2_completion_checklist_includes_closure_verification_commands() -> None:
    checklist = Path("docs/phase2_completion_tasks.md").read_text(encoding="utf-8")

    expected_commands = (
        "pytest tests/test_phase2_task*.py",
        "pytest tests/test_phase2_reliability_gate.py tests/test_phase2_lane_segmentation_robustness.py",
        "pytest tests/",
        "pytest bench/",
        "run_tests.bat",
        "pytest --cov=src/coloursorter --cov-report=xml",
    )

    for command in expected_commands:
        assert f"`{command}`" in checklist
