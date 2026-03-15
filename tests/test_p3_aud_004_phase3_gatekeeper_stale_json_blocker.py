from __future__ import annotations

import json
from pathlib import Path


EVIDENCE_BUNDLE_PATH = Path("docs/artifacts/phase3/phase3_evidence_bundle.json")
GATEKEEPER_AUDIT_PATH = Path("docs/artifacts/phase3/phase3_gatekeeper_audit.md")


def test_p3_aud_004_gatekeeper_report_contains_stale_invalid_json_blocker() -> None:
    payload = json.loads(EVIDENCE_BUNDLE_PATH.read_text(encoding="utf-8"))
    report = GATEKEEPER_AUDIT_PATH.read_text(encoding="utf-8")

    assert payload["task_id"] == "T3-006"
    assert payload["phase"] == "phase3"
    assert payload["overall_ok"] is True

    assert "`docs/artifacts/phase3/phase3_evidence_bundle.json` cannot be parsed as JSON." in report
    assert "1. Invalid JSON in canonical Phase 3 evidence artifact (`docs/artifacts/phase3/phase3_evidence_bundle.json`)." in report
