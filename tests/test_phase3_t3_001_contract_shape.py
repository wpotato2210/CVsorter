from __future__ import annotations

import json
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/protocol_vectors_t3_001.json")


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return payload


def test_t3_001_fixture_vector_order_is_stable() -> None:
    payload = _load_fixture()
    assert payload["vector_pack"] == "T3-001"

    vector_ids = [vector["id"] for vector in payload["vectors"]]
    assert vector_ids == [
        "hello_sync",
        "heartbeat_ready",
        "set_mode_manual",
        "sched_enqueue",
        "get_state_snapshot",
        "reset_queue",
    ]


def test_t3_001_fixture_ack_schema_shape_is_stable() -> None:
    payload = _load_fixture()

    for vector in payload["vectors"]:
        expected_response = vector["expected_response"]
        assert expected_response["command"] == "ACK"
        args = expected_response["args"]
        assert len(args) == 5
        assert args[0] in {"AUTO", "MANUAL"}
        assert str(args[1]).isdigit()
        assert args[2] in {"IDLE", "ACTIVE"}
        assert args[3] in {"true", "false"}
        assert args[4] in {"SYNCING", "READY"}
