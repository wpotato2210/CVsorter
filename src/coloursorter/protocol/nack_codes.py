from __future__ import annotations

from typing import Final

from .constants import (
    NACK_ARG_COUNT_MISMATCH,
    NACK_ARG_RANGE_ERROR,
    NACK_ARG_TYPE_ERROR,
    NACK_BUSY,
    NACK_INVALID_MODE_TRANSITION,
    NACK_MALFORMED_FRAME,
    NACK_QUEUE_FULL,
    NACK_UNKNOWN_COMMAND,
)

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

CANONICAL_NACK_7: Final[tuple[int, str]] = (NACK_BUSY, DETAIL_BUSY)


def canonical_detail_for_code(code: int) -> str | None:
    return NACK_CODE_TO_DETAIL.get(code)


def is_canonical_nack(code: int | None, detail: str | None) -> bool:
    if code is None:
        return False
    expected = canonical_detail_for_code(code)
    if expected is None:
        return False
    return (detail or "").strip().upper() == expected
