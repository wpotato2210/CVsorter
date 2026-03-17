from __future__ import annotations

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path


SNAPSHOT_PATH = Path("tests/fixtures/phase3_evidence_bundle_t3_006_verify_only_snapshot.json")


def test_st_006_verify_only_snapshot_is_byte_stable() -> None:
    snapshot_bytes = SNAPSHOT_PATH.read_bytes()
    digest = sha256(snapshot_bytes).hexdigest()
    assert digest == "0f44071d86f5073429bef3e893ab376c9f288cccbeaf3352f986c7e0f482f8b7"


def test_st_006_verify_only_output_matches_snapshot() -> None:
    completed = subprocess.run(
        [sys.executable, "tools/phase3_evidence_bundle.py", "--verify-only"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr

    expected_payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    actual_payload = json.loads(completed.stdout)

    assert list(actual_payload.keys()) == [
        "checks",
        "deterministic_inputs",
        "fingerprints",
        "overall_ok",
        "phase",
        "task_id",
    ]
    assert actual_payload == expected_payload
