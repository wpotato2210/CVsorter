from __future__ import annotations

import json
from pathlib import Path


EVIDENCE_BUNDLE_PATH = Path("docs/artifacts/phase3/phase3_evidence_bundle.json")
GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")


def test_p3_aud_005_gatekeeper_decision_conflicts_with_green_bundle_signal() -> None:
    payload = json.loads(EVIDENCE_BUNDLE_PATH.read_text(encoding="utf-8"))
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert payload["task_id"] == "T3-006"
    assert payload["overall_ok"] is True
    assert "**DO NOT CLOSE PHASE 3**" in report
    assert "Reason: high-severity evidence integrity and verification-scope gaps remain" in report
