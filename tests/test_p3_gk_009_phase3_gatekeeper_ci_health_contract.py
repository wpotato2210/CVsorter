from __future__ import annotations

from pathlib import Path


GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")
REQUIRED_CI_LINES = (
    "- CI workflows exist for packaging, test+coverage, and GUI transition gate in `.github/workflows/ci.yml`.",
    "- CI test job correctly installs `[test]` extras and enforces `coverage.xml` existence.",
    "- Hardware readiness strict workflow exists in `.github/workflows/hardware-readiness-gate.yml`.",
    "- Risk state: local Phase 3 closure command parity is currently broken in this environment (coverage plugin missing), while CI likely passes due explicit dependency install. This is an environment parity risk, not direct CI misconfiguration.",
)


def test_p3_gk_009_phase3_gatekeeper_ci_health_contract_is_traceable() -> None:
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert "## CI/CD HEALTH" in report
    assert "## ARCHITECTURE RISKS" in report

    ci_section = report.split("## CI/CD HEALTH", maxsplit=1)[1].split("## ARCHITECTURE RISKS", maxsplit=1)[0]

    for line in REQUIRED_CI_LINES:
        assert line in ci_section
