from __future__ import annotations

import pytest

from coloursorter.protocol import OpenSpecV3Host
from coloursorter.protocol.nack_codes import (
    DETAIL_ARG_COUNT_MISMATCH,
    DETAIL_ARG_RANGE_ERROR,
    DETAIL_ARG_TYPE_ERROR,
    DETAIL_BUSY,
    DETAIL_INVALID_MODE_TRANSITION,
    DETAIL_MALFORMED_FRAME,
    DETAIL_QUEUE_FULL,
    DETAIL_UNKNOWN_COMMAND,
    NACK_CODE_TO_DETAIL,
    canonical_detail_for_code,
    is_canonical_nack,
)
from coloursorter.serial_interface import FrameFormatError, parse_ack_tokens, parse_frame, serialize_packet


def _response_tokens(frame: str) -> list[str]:
    parsed = parse_frame(frame)
    return [parsed.command, *parsed.args]


@pytest.mark.parametrize(
    "malformed_frame",
    [
        "SCHED|1,10.0|BADCRC",
        "<1|SCHED|1,10.0|DEADBEEF>",
        "<1|SCHED|1,10.0|AAAAAAA>",
        "<1|SCHED|1,10.0|GGGGGGGG>",
        "<1|SCHED|1,10.0>",
    ],
)
def test_malformed_frames_are_deterministically_mapped_to_nack_8(malformed_frame: str) -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    first = parse_ack_tokens(_response_tokens(host.handle_frame(malformed_frame)))
    second = parse_ack_tokens(_response_tokens(host.handle_frame(malformed_frame)))

    assert first.status == "NACK"
    assert first.nack_code == 8
    assert first.detail == DETAIL_MALFORMED_FRAME
    assert second == first


def test_parser_rejects_malformed_frame_before_dispatch_side_effects() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)
    host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"))
    host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2"))

    with pytest.raises(FrameFormatError):
        parse_frame("<3|SCHED|0,10.0|DEADBEEF>")

    before = list(host.queue)
    response = parse_ack_tokens(_response_tokens(host.handle_frame("<3|SCHED|0,10.0|DEADBEEF>")))
    after = list(host.queue)

    assert response.status == "NACK"
    assert response.nack_code == 8
    assert response.detail == DETAIL_MALFORMED_FRAME
    assert before == after


@pytest.mark.parametrize(
    ("code", "detail"),
    [
        (1, DETAIL_UNKNOWN_COMMAND),
        (2, DETAIL_ARG_COUNT_MISMATCH),
        (3, DETAIL_ARG_RANGE_ERROR),
        (4, DETAIL_ARG_TYPE_ERROR),
        (5, DETAIL_INVALID_MODE_TRANSITION),
        (6, DETAIL_QUEUE_FULL),
        (7, DETAIL_BUSY),
        (8, DETAIL_MALFORMED_FRAME),
    ],
)
def test_canonical_nack_mapping_table_is_exact(code: int, detail: str) -> None:
    assert canonical_detail_for_code(code) == detail
    assert NACK_CODE_TO_DETAIL[code] == detail
    assert is_canonical_nack(code, detail)


@pytest.mark.parametrize(
    ("code", "wrong_detail"),
    [
        (7, DETAIL_QUEUE_FULL),
        (8, DETAIL_BUSY),
        (1, DETAIL_ARG_TYPE_ERROR),
    ],
)
def test_wrong_nack_detail_mappings_are_detected(code: int, wrong_detail: str) -> None:
    parsed = parse_ack_tokens(["NACK", str(code), wrong_detail])

    assert parsed.status == "NACK"
    assert parsed.nack_code == code
    assert parsed.detail == wrong_detail
    assert is_canonical_nack(parsed.nack_code, parsed.detail) is False
