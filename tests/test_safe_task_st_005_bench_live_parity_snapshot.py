from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/bench_live_parity_t3_005.json")


def test_st_005_bench_live_parity_fixture_is_byte_stable() -> None:
    fixture_bytes = FIXTURE_PATH.read_bytes()
    digest = sha256(fixture_bytes).hexdigest()
    assert digest == "370a025385d81be50ad5cd74106841b5ea3e722225c3b92e5a93015c43abb58d"


def test_st_005_bench_live_parity_field_order_is_canonical() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert list(payload.keys()) == ["vector_pack", "seed", "vectors"]
    for vector in payload["vectors"]:
        assert list(vector.keys()) == [
            "name",
            "frame",
            "detection",
            "preprocess_metrics",
            "transport_response",
            "expected",
        ]
