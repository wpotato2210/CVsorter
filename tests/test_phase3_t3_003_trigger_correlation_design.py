from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE_PATH = Path("tests/fixtures/trigger_correlation_t3_003.json")


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return payload


def test_t3_003_fixture_is_deterministic_and_ordered() -> None:
    payload = _load_fixture()

    assert payload["vector_pack"] == "T3-003"
    assert payload["seed"] == 3003
    assert payload["status_classes"] == [
        "terminal_acknowledged",
        "terminal_missed_window",
        "terminal_not_observed",
    ]

    vectors = payload["vectors"]
    vector_ids = [vector["id"] for vector in vectors]
    assert vector_ids == [
        "accepted_terminal_acknowledged",
        "accepted_terminal_missed_window",
        "accepted_terminal_not_observed",
    ]


def test_t3_003_correlation_key_is_unique_per_vector() -> None:
    payload = _load_fixture()
    vectors = payload["vectors"]

    keys = [
        (str(vector["msg_id"]), str(vector["command"]), int(vector["lane"]))
        for vector in vectors
    ]
    assert len(keys) == len(set(keys))


@pytest.mark.xfail(
    reason="T3-003 is informational/non-release gating until runtime correlation reconciler lands",
    strict=False,
)
def test_t3_003_placeholder_runtime_reconciler_non_gating() -> None:
    payload = _load_fixture()
    accepted_vectors = [vector for vector in payload["vectors"] if bool(vector["accepted"])]

    reconciled: dict[tuple[str, str, int], str] = {}
    for vector in accepted_vectors:
        key = (str(vector["msg_id"]), str(vector["command"]), int(vector["lane"]))
        reconciled[key] = "pending_runtime_implementation"

    expected = {
        (str(vector["msg_id"]), str(vector["command"]), int(vector["lane"])): str(vector["terminal_status"])
        for vector in accepted_vectors
    }

    assert reconciled == expected
