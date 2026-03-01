from __future__ import annotations

from typing import Final

# OpenSpec v3 canonical NACK details.
NACK_UNKNOWN_COMMAND: Final[int] = 1
NACK_ARG_COUNT_MISMATCH: Final[int] = 2
NACK_ARG_RANGE_ERROR: Final[int] = 3
NACK_ARG_TYPE_ERROR: Final[int] = 4
NACK_INVALID_MODE_TRANSITION: Final[int] = 5
NACK_QUEUE_FULL: Final[int] = 6
NACK_BUSY: Final[int] = 7
NACK_MALFORMED_FRAME: Final[int] = 8

DETAIL_UNKNOWN_COMMAND: Final[str] = "UNKNOWN_COMMAND"
DETAIL_ARG_COUNT_MISMATCH: Final[str] = "ARG_COUNT_MISMATCH"
DETAIL_ARG_RANGE_ERROR: Final[str] = "ARG_RANGE_ERROR"
DETAIL_ARG_TYPE_ERROR: Final[str] = "ARG_TYPE_ERROR"
DETAIL_INVALID_MODE_TRANSITION: Final[str] = "INVALID_MODE_TRANSITION"
DETAIL_QUEUE_FULL: Final[str] = "QUEUE_FULL"
DETAIL_BUSY: Final[str] = "BUSY"
DETAIL_MALFORMED_FRAME: Final[str] = "MALFORMED_FRAME"
DETAIL_SAFE: Final[str] = "SAFE"
DETAIL_WATCHDOG: Final[str] = "WATCHDOG"

NACK_CODE_TO_DETAIL: Final[dict[int, str]] = {
    NACK_UNKNOWN_COMMAND: DETAIL_UNKNOWN_COMMAND,
    NACK_ARG_COUNT_MISMATCH: DETAIL_ARG_COUNT_MISMATCH,
    NACK_ARG_RANGE_ERROR: DETAIL_ARG_RANGE_ERROR,
    NACK_ARG_TYPE_ERROR: DETAIL_ARG_TYPE_ERROR,
    NACK_INVALID_MODE_TRANSITION: DETAIL_INVALID_MODE_TRANSITION,
    NACK_QUEUE_FULL: DETAIL_QUEUE_FULL,
    NACK_BUSY: DETAIL_BUSY,
    NACK_MALFORMED_FRAME: DETAIL_MALFORMED_FRAME,
}


def is_canonical_nack(code: int | None, detail: str | None) -> bool:
    if code is None:
        return False
    expected = NACK_CODE_TO_DETAIL.get(code)
    if expected is None:
        return False
    return (detail or "").strip().upper() == expected
