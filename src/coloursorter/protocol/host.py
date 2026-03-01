from __future__ import annotations

from dataclasses import dataclass, field

from coloursorter.scheduler.output import MAX_TRIGGER_MM, MIN_TRIGGER_MM
from coloursorter.serial_interface import FrameFormatError, parse_frame, serialize_packet


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
            return self._nack(8, "MALFORMED_FRAME")

        cmd = packet.command
        args = packet.args
        if self.busy:
            return self._nack(7, "BUSY")
        if cmd == "SET_MODE":
            return self._set_mode(args)
        if cmd == "SCHED":
            return self._sched(args)
        if cmd == "GET_STATE":
            if args:
                return self._nack(2, "ARG_COUNT_MISMATCH")
            return self._ack(False)
        if cmd == "RESET_QUEUE":
            if args:
                return self._nack(2, "ARG_COUNT_MISMATCH")
            queue_cleared = bool(self.queue)
            self.queue.clear()
            self.scheduler_state = "IDLE"
            return self._ack(queue_cleared)
        return self._nack(1, "UNKNOWN_COMMAND")

    def _set_mode(self, args: tuple[str, ...]) -> str:
        if len(args) != 1:
            return self._nack(2, "ARG_COUNT_MISMATCH")
        target_mode = args[0].upper()
        if target_mode not in {"AUTO", "MANUAL", "SAFE"}:
            return self._nack(4, "ARG_TYPE_ERROR")
        if self.mode == "SAFE" and target_mode == "AUTO":
            return self._nack(5, "INVALID_MODE_TRANSITION")

        queue_cleared = False
        if target_mode != self.mode:
            queue_cleared = bool(self.queue)
            self.queue.clear()
            self.scheduler_state = "IDLE"
            self.mode = target_mode
        return self._ack(queue_cleared)

    def _sched(self, args: tuple[str, ...]) -> str:
        if len(args) != 2:
            return self._nack(2, "ARG_COUNT_MISMATCH")
        try:
            lane = int(args[0])
        except ValueError:
            return self._nack(4, "ARG_TYPE_ERROR")
        try:
            trigger_mm = float(args[1])
        except ValueError:
            return self._nack(4, "ARG_TYPE_ERROR")

        if lane < 0 or lane > 21:
            return self._nack(3, "ARG_RANGE_ERROR")
        if trigger_mm < MIN_TRIGGER_MM or trigger_mm > MAX_TRIGGER_MM:
            return self._nack(3, "ARG_RANGE_ERROR")
        if len(self.queue) >= self.max_queue_depth:
            return self._nack(6, "QUEUE_FULL")

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
