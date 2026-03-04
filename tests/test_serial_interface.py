from __future__ import annotations

import pytest

from coloursorter.serial_interface import (
    FrameFormatError,
    PacketValidationError,
    decode_packet_bytes,
    encode_packet_bytes,
    parse_ack_tokens,
)


def test_encode_decode_round_trip() -> None:
    payload = encode_packet_bytes("sched", (3, "12.000"))
    packet = decode_packet_bytes(payload)
    assert packet.command == "SCHED"
    assert packet.args == ("3", "12.000")


def test_encode_packet_rejects_oversized_frame() -> None:
    oversized_arg = "x" * 300
    with pytest.raises(PacketValidationError):
        encode_packet_bytes("SCHED", (oversized_arg,))


def test_decode_packet_rejects_oversized_payload() -> None:
    oversized_payload = b"<" + (b"x" * 260) + b">"
    with pytest.raises(FrameFormatError):
        decode_packet_bytes(oversized_payload)


def test_parse_ack_tokens_rejects_extra_ack_tokens() -> None:
    with pytest.raises(PacketValidationError):
        parse_ack_tokens(("ACK", "EXTRA"))


def test_parse_ack_tokens_rejects_negative_nack_code() -> None:
    with pytest.raises(PacketValidationError):
        parse_ack_tokens(("NACK", "-1"))
