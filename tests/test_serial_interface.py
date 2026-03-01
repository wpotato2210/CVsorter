from __future__ import annotations

import pytest

from coloursorter.scheduler import ScheduledCommand
from coloursorter.serial_interface import (
    FrameFormatError,
    PacketValidationError,
    decode_packet_bytes,
    encode_schedule_command,
    parse_ack_tokens,
    parse_frame,
    serialize_packet,
)


def test_protocol_framing_round_trip_for_sched_packet() -> None:
    frame = serialize_packet("SCHED", (4, "301.500"))
    parsed = parse_frame(frame)

    assert frame == "<SCHED|4|301.500>"
    assert parsed.command == "SCHED"
    assert parsed.args == ("4", "301.500")


@pytest.mark.parametrize("payload", [b"<SCHED|1|200.000>\n", b"<ACK>\n"])
def test_decode_packet_bytes_accepts_ascii_wire_payload(payload: bytes) -> None:
    parsed = decode_packet_bytes(payload)
    assert parsed.command in {"SCHED", "ACK"}


def test_ack_and_nack_parsing() -> None:
    ack = parse_ack_tokens(["ACK", "AUTO", "3", "ACTIVE", "true"])
    nack = parse_ack_tokens(["NACK", "6", "QUEUE_FULL"])

    assert ack.status == "ACK"
    assert ack.mode == "AUTO"
    assert ack.queue_depth == 3
    assert ack.scheduler_state == "ACTIVE"
    assert ack.queue_cleared is True

    assert nack.status == "NACK"
    assert nack.nack_code == 6
    assert nack.detail == "QUEUE_FULL"


def test_nack_requires_numeric_code() -> None:
    with pytest.raises(PacketValidationError, match="nack_code must be an integer"):
        parse_ack_tokens(["NACK", "NOT_A_NUMBER"])


def test_nack_requires_openspec_range() -> None:
    with pytest.raises(PacketValidationError, match="OpenSpec range 1..8"):
        parse_ack_tokens(["NACK", "0"])


def test_protocol_framing_rejects_malformed_frame() -> None:
    with pytest.raises(FrameFormatError, match="start with '<' and end with '>'"):
        parse_frame("SCHED|1|2")


def test_wire_encoder_serializes_sched_command() -> None:
    payload = encode_schedule_command(ScheduledCommand(lane=9, position_mm=412.3456))
    assert payload == b"<SCHED|9|412.346>\n"


def test_ack_metadata_rejects_negative_queue_depth() -> None:
    with pytest.raises(PacketValidationError, match="queue_depth must be >= 0"):
        parse_ack_tokens(["ACK", "AUTO", "-1", "ACTIVE", "false"])


def test_ack_metadata_rejects_unknown_scheduler_state() -> None:
    with pytest.raises(PacketValidationError, match="scheduler_state must be IDLE or ACTIVE"):
        parse_ack_tokens(["ACK", "AUTO", "1", "PAUSED", "false"])
