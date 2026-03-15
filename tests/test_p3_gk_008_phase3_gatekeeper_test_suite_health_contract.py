from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
REQUIRED_HEALTH_LINES = (
    "- `pytest tests/` -> PASS (`473 passed, 2 skipped, 2 xfailed`).",
    "- `pytest bench/` -> PASS (`1 passed`).",
    "- `./run_tests.bat` -> BLOCKED on Linux (`Permission denied`).",
    "- `pytest --cov=src/coloursorter --cov-report=xml` -> BLOCKED locally (pytest-cov args unavailable).",
    "- `pytest --collect-only -q tests bench` -> successful collection (no code 5 / no-collection silent failure).",
)


def test_p3_gk_008_phase3_gatekeeper_test_suite_health_contract_is_explicit() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert "## TEST SUITE HEALTH" in report
    assert "## CI/CD HEALTH" in report

    health_section = report.split("## TEST SUITE HEALTH", maxsplit=1)[1].split(
        "## CI/CD HEALTH", maxsplit=1
    )[0]

    for line in REQUIRED_HEALTH_LINES:
        assert line in health_section

    assert "Integrity flags:" in health_section
    assert "2 skipped tests are present in executed suite output." in health_section
