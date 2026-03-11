from __future__ import annotations

from coloursorter.protocol.host import OpenSpecV3Host
from coloursorter.serial_interface import parse_frame, serialize_packet


def _ack_tokens(frame: str) -> tuple[str, tuple[str, ...], str]:
    packet = parse_frame(frame)
    return packet.command, packet.args, packet.msg_id


def test_duplicate_msg_id_with_different_payload_is_cached_without_extra_side_effects() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)

    host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"))
    host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2"))

    first = host.handle_frame(serialize_packet("SCHED", ("1", "10.0"), msg_id="42"))
    duplicate_with_different_payload = host.handle_frame(serialize_packet("SCHED", ("2", "20.0"), msg_id="42"))

    assert duplicate_with_different_payload == first
    assert host.queue == [(1, 10.0)]


def test_duplicate_msg_id_for_set_mode_replays_ack_without_reprocessing_transition() -> None:
    host = OpenSpecV3Host(max_queue_depth=4, mode="MANUAL")

    host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"))
    host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2"))
    host.handle_frame(serialize_packet("SCHED", ("1", "10.0"), msg_id="3"))

    first = host.handle_frame(serialize_packet("SET_MODE", ("SAFE",), msg_id="77"))
    duplicate = host.handle_frame(serialize_packet("SET_MODE", ("AUTO",), msg_id="77"))

    command, args, msg_id = _ack_tokens(first)

    assert duplicate == first
    assert command == "ACK"
    assert msg_id == "77"
    assert args[0] == "SAFE"
    assert args[1] == "0"
    assert args[3] == "true"
    assert host.mode == "SAFE"
    assert host.queue == []
