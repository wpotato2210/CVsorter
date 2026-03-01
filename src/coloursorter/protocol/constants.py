from __future__ import annotations

from typing import Final

# Command identifiers (OpenSpec v3 protocol/commands.json)
CMD_SET_MODE: Final[str] = "SET_MODE"
CMD_SCHED: Final[str] = "SCHED"
CMD_GET_STATE: Final[str] = "GET_STATE"
CMD_RESET_QUEUE: Final[str] = "RESET_QUEUE"
SUPPORTED_COMMANDS: Final[frozenset[str]] = frozenset({CMD_SET_MODE, CMD_SCHED, CMD_GET_STATE, CMD_RESET_QUEUE})

# ACK/NACK tokens
ACK_TOKEN: Final[str] = "ACK"
NACK_TOKEN: Final[str] = "NACK"

# SCHED argument ranges
LANE_MIN: Final[int] = 0
LANE_MAX: Final[int] = 21
TRIGGER_MM_MIN: Final[float] = 0.0
TRIGGER_MM_MAX: Final[float] = 2000.0

# Queue limits
DEFAULT_MAX_QUEUE_DEPTH: Final[int] = 8
QUEUE_DEPTH_MIN: Final[int] = 0

# ACK metadata enums
MODE_AUTO: Final[str] = "AUTO"
MODE_MANUAL: Final[str] = "MANUAL"
MODE_SAFE: Final[str] = "SAFE"
ALLOWED_MODES: Final[frozenset[str]] = frozenset({MODE_AUTO, MODE_MANUAL, MODE_SAFE})

SCHEDULER_IDLE: Final[str] = "IDLE"
SCHEDULER_ACTIVE: Final[str] = "ACTIVE"
ALLOWED_SCHEDULER_STATES: Final[frozenset[str]] = frozenset({SCHEDULER_IDLE, SCHEDULER_ACTIVE})

# OpenSpec v3 canonical NACK details.
NACK_UNKNOWN_COMMAND: Final[int] = 1
NACK_ARG_COUNT_MISMATCH: Final[int] = 2
NACK_ARG_RANGE_ERROR: Final[int] = 3
NACK_ARG_TYPE_ERROR: Final[int] = 4
NACK_INVALID_MODE_TRANSITION: Final[int] = 5
NACK_QUEUE_FULL: Final[int] = 6
NACK_BUSY: Final[int] = 7
NACK_MALFORMED_FRAME: Final[int] = 8
NACK_CODE_MIN: Final[int] = NACK_UNKNOWN_COMMAND
NACK_CODE_MAX: Final[int] = NACK_MALFORMED_FRAME

