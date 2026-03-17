from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path


VECTOR_FIXTURE_PATH = Path("tests/fixtures/timing_jitter_t3_002.json")
REPORT_FIXTURE_PATH = Path("tests/fixtures/timing_jitter_t3_002_report_snapshot.json")


def test_st_002_timing_jitter_fixtures_are_byte_stable() -> None:
    vector_digest = sha256(VECTOR_FIXTURE_PATH.read_bytes()).hexdigest()
    report_digest = sha256(REPORT_FIXTURE_PATH.read_bytes()).hexdigest()

    assert vector_digest == "54c6988158610238e726e7f9979311318c838a749a9c69e4cd49e26af3930cfc"
    assert report_digest == "5bc102e97d5aa654fc206bfb5be5bb027e3743d21afae181254f09b071830a82"


def test_st_002_timing_jitter_vector_and_report_field_order_are_canonical() -> None:
    vector_payload = json.loads(VECTOR_FIXTURE_PATH.read_text(encoding="utf-8"))
    report_payload = json.loads(REPORT_FIXTURE_PATH.read_text(encoding="utf-8"))

    assert list(vector_payload.keys()) == ["vector_pack", "seed", "description", "envelope", "vectors"]
    assert list(vector_payload["envelope"].keys()) == [
        "max_jitter_ms",
        "max_missed_window_count",
        "min_reject_reliability",
    ]

    for vector in vector_payload["vectors"]:
        assert list(vector.keys()) == [
            "id",
            "max_jitter_ms",
            "missed_window_count",
            "reject_reliability",
            "expected_pass",
            "expected_hard_gate_pass",
        ]

    assert list(report_payload.keys()) == ["report"]
    for report_row in report_payload["report"]:
        assert list(report_row.keys()) == [
            "id",
            "scenario_pass",
            "hard_gate_pass",
            "reject_reliability",
            "max_jitter_ms",
            "missed_window_count",
        ]
