from __future__ import annotations

from dataclasses import dataclass, field

from coloursorter.scheduler.output import MAX_TRIGGER_MM, MIN_TRIGGER_MM
from coloursorter.serial_interface import FrameFormatError, parse_frame, serialize_packet

from .nack_codes import (
    DETAIL_ARG_COUNT_MISMATCH,
    DETAIL_ARG_RANGE_ERROR,
    DETAIL_ARG_TYPE_ERROR,
    DETAIL_BUSY,
    DETAIL_INVALID_MODE_TRANSITION,
    DETAIL_MALFORMED_FRAME,
    DETAIL_QUEUE_FULL,
    DETAIL_UNKNOWN_COMMAND,
    NACK_ARG_COUNT_MISMATCH,
    NACK_ARG_RANGE_ERROR,
    NACK_ARG_TYPE_ERROR,
    NACK_BUSY,
    NACK_INVALID_MODE_TRANSITION,
    NACK_MALFORMED_FRAME,
    NACK_QUEUE_FULL,
    NACK_UNKNOWN_COMMAND,
)
from .policy import is_mode_transition_allowed


@dataclass
class OpenSpecV3Host:
    max_queue_depth: int = 8
    mode: str = "AUTO"
    scheduler_state: str = "IDLE"
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
            return self._nack(NACK_BUSY, DETAIL_BUSY)
        if cmd == "SET_MODE":
            return self._set_mode(args)
        if cmd == "SCHED":
            return self._sched(args)
        if cmd == "GET_STATE":
            if args:
                return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH)
            return self._ack(False)
        if cmd == "RESET_QUEUE":
            if args:
                return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH)
            queue_cleared = bool(self.queue)
            self.queue.clear()
            self.scheduler_state = "IDLE"
            return self._ack(queue_cleared)
        return self._nack(NACK_UNKNOWN_COMMAND, DETAIL_UNKNOWN_COMMAND)

    def _set_mode(self, args: tuple[str, ...]) -> str:
        if len(args) != 1:
            return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH)
        target_mode = args[0].upper()
        if target_mode not in {"AUTO", "MANUAL", "SAFE"}:
            return self._nack(NACK_ARG_TYPE_ERROR, DETAIL_ARG_TYPE_ERROR)
        if not is_mode_transition_allowed(self.mode, target_mode):
            return self._nack(NACK_INVALID_MODE_TRANSITION, DETAIL_INVALID_MODE_TRANSITION)

        queue_cleared = False
        if target_mode != self.mode:
            queue_cleared = bool(self.queue)
            self.queue.clear()
            self.scheduler_state = "IDLE"
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

        if lane < 0 or lane > 21:
            return self._nack(NACK_ARG_RANGE_ERROR, DETAIL_ARG_RANGE_ERROR)
        if trigger_mm < MIN_TRIGGER_MM or trigger_mm > MAX_TRIGGER_MM:
            return self._nack(NACK_ARG_RANGE_ERROR, DETAIL_ARG_RANGE_ERROR)
        if len(self.queue) >= self.max_queue_depth:
            return self._nack(NACK_QUEUE_FULL, DETAIL_QUEUE_FULL)

        self.queue.append((lane, trigger_mm))
        self.scheduler_state = "ACTIVE"
        return self._ack(False)

    def _ack(self, queue_cleared: bool) -> str:
        return serialize_packet(
            "ACK",
            (
                self.mode,
                str(len(self.queue)),
                self.scheduler_state,
                str(queue_cleared).lower(),
            ),
        )

    @staticmethod
    def _nack(code: int, detail: str) -> str:
        return serialize_packet("NACK", (str(code), detail))
