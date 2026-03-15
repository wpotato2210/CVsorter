from __future__ import annotations

import json
from pathlib import Path


BUNDLE_PATH = Path("docs/artifacts/phase3/phase3_evidence_bundle.json")
EXPECTED_CHECK_KEYS = (
    "protocol_parity",
    "timing_envelope",
    "trigger_correlation",
    "hil_repeatability",
)


def test_p3_aud_001_phase3_evidence_bundle_is_valid_json_with_expected_contract() -> None:
    payload = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))

    assert payload["task_id"] == "T3-006"
    assert payload["phase"] == "phase3"
    assert payload["overall_ok"] is True

    checks = payload["checks"]
    assert sorted(checks.keys()) == sorted(EXPECTED_CHECK_KEYS)
    for key in EXPECTED_CHECK_KEYS:
        assert checks[key]["ok"] is True
        assert checks[key]["detail"] == "ok"
