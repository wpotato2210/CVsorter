from __future__ import annotations

import pytest

from coloursorter.scheduler import ScheduledCommand
from coloursorter.serial_interface import (
    AckSensorAdapter,
    ActuationRequest,
    ActuationResponse,
    FrameFormatError,
    PacketValidationError,
    WireActuatorAdapter,
    decode_packet_bytes,
    encode_schedule_command,
    parse_ack_tokens,
    parse_frame,
    serialize_packet,
)


def test_protocol_framing_round_trip_for_sched_packet() -> None:
    frame = serialize_packet("SCHED", (4, "301.500"), msg_id="17")
    parsed = parse_frame(frame)

    assert frame.startswith("<17|SCHED|4,301.500|")
    assert parsed.msg_id == "17"
    assert parsed.command == "SCHED"
    assert parsed.args == ("4", "301.500")


@pytest.mark.parametrize(
    "payload",
    [
        encode_schedule_command(ScheduledCommand(lane=1, position_mm=200.0)),
        serialize_packet("ACK", (), msg_id="2").encode() + b"\n",
    ],
)
def test_decode_packet_bytes_accepts_ascii_wire_payload(payload: bytes) -> None:
    parsed = decode_packet_bytes(payload)
    assert parsed.command in {"SCHED", "ACK"}


def test_ack_and_nack_parsing() -> None:
    ack = parse_ack_tokens(["ACK", "AUTO", "3", "ACTIVE", "true", "READY"])
    nack = parse_ack_tokens(["NACK", "6", "QUEUE_FULL"])

    assert ack.status == "ACK"
    assert ack.mode == "AUTO"
    assert ack.queue_depth == 3
    assert ack.scheduler_state == "ACTIVE"
    assert ack.queue_cleared is True
    assert ack.link_state == "READY"

    assert nack.status == "NACK"
    assert nack.nack_code == 6
    assert nack.detail == "QUEUE_FULL"


def test_crc_validation_rejects_tampered_frame() -> None:
    with pytest.raises(FrameFormatError, match="crc mismatch"):
        parse_frame("<1|SCHED|1,200.000|DEADBEEF>")


def test_protocol_framing_rejects_oversized_frame() -> None:
    with pytest.raises(FrameFormatError, match="exceeds max length"):
        parse_frame("<" + ("A" * 300) + ">")


def test_protocol_framing_rejects_non_hex_crc() -> None:
    with pytest.raises(FrameFormatError, match="crc must be 8 uppercase hex"):
        parse_frame("<1|SCHED|1,200.000|ZZZZZZZZ>")


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
    assert payload.startswith(b"<0|SCHED|9,412.346|")


def test_ack_metadata_rejects_negative_queue_depth() -> None:
    with pytest.raises(PacketValidationError, match="queue_depth must be >= 0"):
        parse_ack_tokens(["ACK", "AUTO", "-1", "ACTIVE", "false"])


def test_ack_metadata_rejects_unknown_scheduler_state() -> None:
    with pytest.raises(PacketValidationError, match="scheduler_state must be IDLE or ACTIVE"):
        parse_ack_tokens(["ACK", "AUTO", "1", "PAUSED", "false"])


def test_ack_metadata_rejects_non_alnum_link_state() -> None:
    with pytest.raises(PacketValidationError, match="alphanumeric/underscore"):
        parse_ack_tokens(["ACK", "AUTO", "1", "ACTIVE", "false", "READY-"])


def test_nack_detail_rejects_oversized_payload() -> None:
    with pytest.raises(PacketValidationError, match="detail exceeds max length"):
        parse_ack_tokens(["NACK", "2", "X" * 129])


def test_wire_actuator_adapter_encodes_sched_request() -> None:
    adapter = WireActuatorAdapter()
    payload = adapter.encode_actuation(
        ActuationRequest(
            command=ScheduledCommand(lane=2, position_mm=123.456),
            msg_id="42",
        )
    )
    assert payload.startswith(b"<42|SCHED|2,123.456|")


def test_ack_sensor_adapter_maps_ack_to_sensor_snapshot() -> None:
    adapter = AckSensorAdapter()
    ack = parse_ack_tokens(["ACK", "MANUAL", "4", "ACTIVE", "false", "READY"])

    snapshot = adapter.decode_response(ActuationResponse(ack=ack, msg_id="42"))

    assert snapshot.mode == "MANUAL"
    assert snapshot.queue_depth == 4
    assert snapshot.scheduler_state == "ACTIVE"
    assert snapshot.queue_cleared is False
    assert snapshot.link_state == "READY"
