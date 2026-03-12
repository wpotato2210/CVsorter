from __future__ import annotations

import pytest

from coloursorter.protocol.constants import CMD_HEARTBEAT
from coloursorter.protocol.host import OpenSpecV3Host
from coloursorter.serial_interface import PacketValidationError, parse_ack_tokens, parse_frame, serialize_packet


def _tokens(frame: str) -> list[str]:
    parsed = parse_frame(frame)
    return [parsed.command, *parsed.args]


def test_protocol_rejects_missing_hello_fields_deterministically() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    ack = parse_ack_tokens(_tokens(host.handle_frame(serialize_packet("HELLO", ("3.1",), msg_id="1"))))

    assert ack.status == "NACK"
    assert ack.nack_code == 2
    assert ack.detail == "ARG_COUNT_MISMATCH"


def test_protocol_enforces_version_compatibility() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    ack = parse_ack_tokens(_tokens(host.handle_frame(serialize_packet("HELLO", ("99.9", "SCHED"), msg_id="2"))))

    assert ack.status == "NACK"
    assert ack.nack_code == 3
    assert ack.detail == "ARG_RANGE_ERROR"


def test_protocol_rejects_ack_payload_missing_required_schema_fields() -> None:
    with pytest.raises(PacketValidationError, match=r"ACK metadata must be mode\|queue_depth\|scheduler_state\|queue_cleared\|\[link_state\]"):
        parse_ack_tokens(["ACK", "AUTO", "1", "ACTIVE"])


def test_protocol_heartbeat_without_handshake_is_rejected() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    ack = parse_ack_tokens(_tokens(host.handle_frame(serialize_packet(CMD_HEARTBEAT, (), msg_id="3"))))

    assert ack.status == "NACK"
    assert ack.nack_code == 5
    assert ack.detail == "INVALID_MODE_TRANSITION"
