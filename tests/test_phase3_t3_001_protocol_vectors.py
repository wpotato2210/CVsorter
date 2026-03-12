from __future__ import annotations

import json
from pathlib import Path

from coloursorter.protocol import OpenSpecV3Host
from coloursorter.serial_interface import parse_ack_tokens, parse_frame, serialize_packet


FIXTURE_PATH = Path("tests/fixtures/protocol_vectors_t3_001.json")


def _load_vectors() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload["vectors"]
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return vectors


def test_t3_001_command_frames_are_deterministic() -> None:
    vectors = _load_vectors()
    for vector in vectors:
        request = vector["request"]
        frame = serialize_packet(
            str(request["command"]),
            tuple(str(arg) for arg in request["args"]),
            msg_id=str(request["msg_id"]),
        )
        assert frame == request["frame"]


def test_t3_001_vector_pack_host_conformance_and_token_ordering() -> None:
    vectors = _load_vectors()
    host = OpenSpecV3Host(max_queue_depth=3)

    for vector in vectors:
        request = vector["request"]
        expected_response = vector["expected_response"]

        request_frame = serialize_packet(
            str(request["command"]),
            tuple(str(arg) for arg in request["args"]),
            msg_id=str(request["msg_id"]),
        )
        assert request_frame == request["frame"]

        parsed_request = parse_frame(request_frame)
        assert parsed_request.command == request["command"]
        assert parsed_request.args == tuple(request["args"])

        response_frame = host.handle_frame(request_frame)
        assert response_frame == expected_response["frame"]

        parsed_response = parse_frame(response_frame)
        assert parsed_response.command == expected_response["command"]
        assert parsed_response.args == tuple(expected_response["args"])

        ack = parse_ack_tokens([parsed_response.command, *parsed_response.args])
        assert ack.status == "ACK"
        assert ack.mode == expected_response["args"][0]
        assert ack.queue_depth == int(expected_response["args"][1])
        assert ack.scheduler_state == expected_response["args"][2]
        assert ack.queue_cleared is (expected_response["args"][3] == "true")
        assert ack.link_state == expected_response["args"][4]
