from __future__ import annotations

from coloursorter.protocol.host import OpenSpecV3Host
from coloursorter.serial_interface import parse_ack_tokens, parse_frame, serialize_packet


def _run_protocol_executor_sequence() -> list[str]:
    host = OpenSpecV3Host(max_queue_depth=1)
    requests = [
        serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"),
        serialize_packet("HEARTBEAT", (), msg_id="2"),
        serialize_packet("SET_MODE", ("MANUAL",), msg_id="3"),
        serialize_packet("SCHED", (1, "10.0"), msg_id="4"),
        serialize_packet("SCHED", (2, "20.0"), msg_id="5"),
        serialize_packet("SET_MODE", ("AUTO",), msg_id="6"),
        serialize_packet("UNKNOWN", (), msg_id="7"),
        "<8|SCHED|1,10.0|DEADBEEF>",
    ]
    return [host.handle_frame(frame) for frame in requests]


def test_phase3_1_protocol_executor_byte_identical_replay() -> None:
    expected_responses = [
        "<1|ACK|AUTO,0,IDLE,false,SYNCING|6F32C4F5>",
        "<2|ACK|AUTO,0,IDLE,false,READY|050E5912>",
        "<3|ACK|MANUAL,0,IDLE,false,READY|028F6121>",
        "<4|ACK|MANUAL,1,ACTIVE,false,READY|C56E3FCB>",
        "<5|NACK|6,QUEUE_FULL|76814E08>",
        "<6|ACK|AUTO,0,IDLE,true,READY|6C5C7335>",
        "<7|NACK|1,UNKNOWN_COMMAND|C58A13FB>",
        "<0|NACK|8,MALFORMED_FRAME|E40AC433>",
    ]

    run_a = _run_protocol_executor_sequence()
    run_b = _run_protocol_executor_sequence()

    assert run_a == expected_responses
    assert run_b == expected_responses
    assert run_a == run_b


def test_phase3_1_protocol_executor_nack_mapping_is_stable() -> None:
    responses = _run_protocol_executor_sequence()

    queue_full = parse_ack_tokens([*([parse_frame(responses[4]).command]), *parse_frame(responses[4]).args])
    unknown = parse_ack_tokens([*([parse_frame(responses[6]).command]), *parse_frame(responses[6]).args])
    malformed = parse_ack_tokens([*([parse_frame(responses[7]).command]), *parse_frame(responses[7]).args])

    assert (queue_full.status, queue_full.nack_code, queue_full.detail) == ("NACK", 6, "QUEUE_FULL")
    assert (unknown.status, unknown.nack_code, unknown.detail) == ("NACK", 1, "UNKNOWN_COMMAND")
    assert (malformed.status, malformed.nack_code, malformed.detail) == ("NACK", 8, "MALFORMED_FRAME")
