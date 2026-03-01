from __future__ import annotations

from dataclasses import dataclass, field

from coloursorter.serial_interface import FrameFormatError, parse_frame, serialize_packet

from .constants import (
    ACK_TOKEN,
    ALLOWED_MODES,
    CMD_GET_STATE,
    CMD_RESET_QUEUE,
    CMD_SCHED,
    CMD_SET_MODE,
    DEFAULT_MAX_QUEUE_DEPTH,
    LANE_MAX,
    LANE_MIN,
    MODE_AUTO,
    NACK_TOKEN,
    SCHEDULER_ACTIVE,
    SCHEDULER_IDLE,
    TRIGGER_MM_MAX,
    TRIGGER_MM_MIN,
)
from .nack_codes import (
    CANONICAL_NACK_7,
    DETAIL_ARG_COUNT_MISMATCH,
    DETAIL_ARG_RANGE_ERROR,
    DETAIL_ARG_TYPE_ERROR,
    DETAIL_INVALID_MODE_TRANSITION,
    DETAIL_MALFORMED_FRAME,
    DETAIL_QUEUE_FULL,
    DETAIL_UNKNOWN_COMMAND,
    NACK_ARG_COUNT_MISMATCH,
    NACK_ARG_RANGE_ERROR,
    NACK_ARG_TYPE_ERROR,
    NACK_INVALID_MODE_TRANSITION,
    NACK_MALFORMED_FRAME,
    NACK_QUEUE_FULL,
    NACK_UNKNOWN_COMMAND,
)
from .policy import is_mode_transition_allowed


@dataclass
class OpenSpecV3Host:
    max_queue_depth: int = DEFAULT_MAX_QUEUE_DEPTH
    mode: str = MODE_AUTO
    scheduler_state: str = SCHEDULER_IDLE
    queue: list[tuple[int, float]] = field(default_factory=list)
    busy: bool = False

    def handle_frame(self, frame: str) -> str:
        try:
            packet = parse_frame(frame)
        except FrameFormatError:
            return self._nack(NACK_MALFORMED_FRAME, DETAIL_MALFORMED_FRAME)

        cmd = packet.command
        args = packet.args
        if self.busy:
            return self._nack(*CANONICAL_NACK_7)
        if cmd == CMD_SET_MODE:
            return self._set_mode(args)
        if cmd == CMD_SCHED:
            return self._sched(args)
        if cmd == CMD_GET_STATE:
            if args:
                return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH)
            return self._ack(False)
        if cmd == CMD_RESET_QUEUE:
            if args:
                return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH)
            queue_cleared = bool(self.queue)
            self.queue.clear()
            self.scheduler_state = SCHEDULER_IDLE
            return self._ack(queue_cleared)
        return self._nack(NACK_UNKNOWN_COMMAND, DETAIL_UNKNOWN_COMMAND)

    def _set_mode(self, args: tuple[str, ...]) -> str:
        if len(args) != 1:
            return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH)
        target_mode = args[0].upper()
        if target_mode not in ALLOWED_MODES:
            return self._nack(NACK_ARG_TYPE_ERROR, DETAIL_ARG_TYPE_ERROR)
        if not is_mode_transition_allowed(self.mode, target_mode):
            return self._nack(NACK_INVALID_MODE_TRANSITION, DETAIL_INVALID_MODE_TRANSITION)

        queue_cleared = False
        if target_mode != self.mode:
            queue_cleared = bool(self.queue)
            self.queue.clear()
            self.scheduler_state = SCHEDULER_IDLE
            self.mode = target_mode
        return self._ack(queue_cleared)

    def _sched(self, args: tuple[str, ...]) -> str:
        if len(args) != 2:
            return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH)
        try:
            lane = int(args[0])
        except ValueError:
            return self._nack(NACK_ARG_TYPE_ERROR, DETAIL_ARG_TYPE_ERROR)
        try:
            trigger_mm = float(args[1])
        except ValueError:
            return self._nack(NACK_ARG_TYPE_ERROR, DETAIL_ARG_TYPE_ERROR)

        if lane < LANE_MIN or lane > LANE_MAX:
            return self._nack(NACK_ARG_RANGE_ERROR, DETAIL_ARG_RANGE_ERROR)
        if trigger_mm < TRIGGER_MM_MIN or trigger_mm > TRIGGER_MM_MAX:
            return self._nack(NACK_ARG_RANGE_ERROR, DETAIL_ARG_RANGE_ERROR)
        if len(self.queue) >= self.max_queue_depth:
            return self._nack(NACK_QUEUE_FULL, DETAIL_QUEUE_FULL)

        self.queue.append((lane, trigger_mm))
        self.scheduler_state = SCHEDULER_ACTIVE
        return self._ack(False)

    def _ack(self, queue_cleared: bool) -> str:
        return serialize_packet(
            ACK_TOKEN,
            (
                self.mode,
                str(len(self.queue)),
                self.scheduler_state,
                str(queue_cleared).lower(),
            ),
        )

    @staticmethod
    def _nack(code: int, detail: str) -> str:
        return serialize_packet(NACK_TOKEN, (str(code), detail))
