from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/hil_gate_t3_004.json")


def test_st_004_hil_gate_fixture_is_byte_stable() -> None:
    fixture_bytes = FIXTURE_PATH.read_bytes()
    digest = sha256(fixture_bytes).hexdigest()
    assert digest == "a3ed5a24e2190f792db50d1d9e1a38d3f27a44c94da6ceeb1a0da304a2c9d3a8"


def test_st_004_hil_gate_field_order_is_canonical() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert list(payload.keys()) == ["vector_pack", "seed", "runs"]
    for run in payload["runs"]:
        assert list(run.keys()) == [
            "scenario_id",
            "run_index",
            "trace_hash",
            "expected_status",
        ]
