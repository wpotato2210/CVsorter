from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/protocol_vectors_t3_001.json")


def test_st_001_protocol_vector_fixture_is_byte_stable() -> None:
    fixture_bytes = FIXTURE_PATH.read_bytes()
    digest = sha256(fixture_bytes).hexdigest()
    assert digest == "3f6f7ae1f30efb321bbacd3be37d14aa22116d53d2c8568168aeaa3daae266de"


def test_st_001_protocol_vector_field_order_is_canonical() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload["vectors"]

    for vector in vectors:
        assert list(vector.keys()) == ["id", "request", "expected_response"]
        assert list(vector["request"].keys()) == ["msg_id", "command", "args", "frame"]
        assert list(vector["expected_response"].keys()) == ["command", "args", "frame"]
