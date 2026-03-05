from __future__ import annotations

from coloursorter.protocol.host import OpenSpecV3Host
from coloursorter.serial_interface import parse_ack_tokens, parse_frame, serialize_packet


def _tokens(frame: str) -> list[str]:
    parsed = parse_frame(frame)
    return [parsed.command, *parsed.args]


def _ack(frame: str):
    return parse_ack_tokens(_tokens(frame))


def _run_fixed_vectors() -> tuple[list[int], list[str]]:
    host = OpenSpecV3Host(max_queue_depth=2)
    vectors = [
        serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"),
        serialize_packet("HEARTBEAT", (), msg_id="2"),
        serialize_packet("GET_STATE", (), msg_id="3"),
        serialize_packet("SCHED", (1, "10.0"), msg_id="4"),
        serialize_packet("SCHED", (2, "20.0"), msg_id="5"),
        serialize_packet("SCHED", (3, "30.0"), msg_id="6"),
        serialize_packet("RESET_QUEUE", (), msg_id="7"),
        serialize_packet("GET_STATE", (), msg_id="8"),
        serialize_packet("SET_MODE", ("SAFE",), msg_id="9"),
    ]

    queue_depth_trace: list[int] = []
    scheduler_state_trace: list[str] = []
    for frame in vectors:
        ack = _ack(host.handle_frame(frame))
        if ack.status == "ACK":
            queue_depth_trace.append(ack.queue_depth or 0)
            scheduler_state_trace.append(ack.scheduler_state or "")
    return queue_depth_trace, scheduler_state_trace


def test_parser_rejects_crc_invalid_frame_before_dispatch() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)
    host._sched = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("dispatch should not execute"))  # type: ignore[method-assign]

    malformed = "<1|SCHED|1,10.0|DEADBEEF>"
    response = _ack(host.handle_frame(malformed))

    assert response.status == "NACK"
    assert response.nack_code == 8
    assert response.detail == "MALFORMED_FRAME"
    assert host.queue == []


def test_every_command_path_returns_canonical_ack_or_nack() -> None:
    host = OpenSpecV3Host(max_queue_depth=1)

    frames = [
        serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"),
        serialize_packet("HEARTBEAT", (), msg_id="2"),
        serialize_packet("GET_STATE", (), msg_id="3"),
        serialize_packet("SCHED", (1, "10.0"), msg_id="4"),
        serialize_packet("SCHED", (2, "20.0"), msg_id="5"),
        serialize_packet("RESET_QUEUE", (), msg_id="6"),
        serialize_packet("SET_MODE", ("SAFE",), msg_id="7"),
        serialize_packet("SET_MODE", ("AUTO",), msg_id="8"),
        serialize_packet("UNKNOWN", (), msg_id="9"),
    ]

    for frame in frames:
        ack = _ack(host.handle_frame(frame))
        assert ack.status in {"ACK", "NACK"}
        if ack.status == "ACK":
            assert ack.mode in {"AUTO", "MANUAL", "SAFE"}
            assert ack.queue_depth is not None and ack.queue_depth >= 0
            assert ack.scheduler_state in {"IDLE", "ACTIVE"}
            assert isinstance(ack.queue_cleared, bool)
        else:
            assert ack.nack_code is not None and 1 <= ack.nack_code <= 8
            assert ack.detail


def test_queue_and_state_mutations_are_bounded_and_snapshot_safe() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"))
    host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2"))

    first = _ack(host.handle_frame(serialize_packet("SCHED", (1, "10.0"), msg_id="3")))
    second = _ack(host.handle_frame(serialize_packet("SCHED", (2, "20.0"), msg_id="4")))
    full = _ack(host.handle_frame(serialize_packet("SCHED", (3, "30.0"), msg_id="5")))
    reset = _ack(host.handle_frame(serialize_packet("RESET_QUEUE", (), msg_id="6")))
    state = _ack(host.handle_frame(serialize_packet("GET_STATE", (), msg_id="7")))

    assert first.queue_depth == 1 and first.scheduler_state == "ACTIVE"
    assert second.queue_depth == 2 and second.scheduler_state == "ACTIVE"
    assert full.status == "NACK" and full.nack_code == 6
    assert len(host.queue) <= host.max_queue_depth
    assert reset.status == "ACK" and reset.queue_cleared is True
    assert state.status == "ACK" and state.queue_depth == 0 and state.scheduler_state == "IDLE"


def test_conformance_fixed_vectors_are_repeatable_and_identical() -> None:
    depth_a, state_a = _run_fixed_vectors()
    depth_b, state_b = _run_fixed_vectors()

    assert depth_a == [0, 0, 0, 1, 2, 0, 0, 0]
    assert state_a == ["IDLE", "IDLE", "IDLE", "ACTIVE", "ACTIVE", "IDLE", "IDLE", "IDLE"]
    assert depth_a == depth_b
    assert state_a == state_b
