from __future__ import annotations

import json
from pathlib import Path

from coloursorter.protocol.host import OpenSpecV3Host
from coloursorter.serial_interface import parse_frame

FIXTURE_PATH = Path("tests/fixtures/protocol_vectors_t3_001.json")
REQUIRED_COMMAND_SEQUENCE = (
    "HELLO",
    "HEARTBEAT",
    "SET_MODE",
    "SCHED",
    "GET_STATE",
    "RESET_QUEUE",
)


def _vectors() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload["vectors"]
    if not isinstance(vectors, list):
        raise AssertionError("vectors must be a list")
    return vectors


def test_phase3_1_fixture_covers_required_protocol_executor_commands() -> None:
    vectors = _vectors()
    seen_order = [str(vector["request"]["command"]) for vector in vectors]  # type: ignore[index]

    for required in REQUIRED_COMMAND_SEQUENCE:
        assert required in seen_order

    first_occurrence = []
    for required in REQUIRED_COMMAND_SEQUENCE:
        first_occurrence.append(seen_order.index(required))
    assert first_occurrence == sorted(first_occurrence)


def test_phase3_1_vector_replay_is_byte_identical_across_runs() -> None:
    vectors = _vectors()

    def run_once() -> list[str]:
        host = OpenSpecV3Host(max_queue_depth=3)
        return [host.handle_frame(str(vector["request"]["frame"])) for vector in vectors]  # type: ignore[index]

    run_a = run_once()
    run_b = run_once()

    assert run_a == run_b

    for vector, response in zip(vectors, run_a, strict=True):
        expected = str(vector["expected_response"]["frame"])  # type: ignore[index]
        assert response == expected
        parsed = parse_frame(response)
        assert parsed.command == str(vector["expected_response"]["command"])  # type: ignore[index]
