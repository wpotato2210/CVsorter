from __future__ import annotations

import time
from dataclasses import dataclass, field

from coloursorter.serial_interface import FrameFormatError, parse_frame, serialize_packet

from .constants import (
    ACK_TOKEN,
    ALLOWED_MODES,
    CMD_GET_STATE,
    CMD_HEARTBEAT,
    CMD_HELLO,
    CMD_RESET_QUEUE,
    CMD_SCHED,
    CMD_SET_MODE,
    DEFAULT_MAX_QUEUE_DEPTH,
    LANE_MAX,
    LANE_MIN,
    LINK_DEGRADED,
    LINK_DISCONNECTED,
    LINK_READY,
    LINK_SYNCING,
    MODE_AUTO,
    SCHEDULER_ACTIVE,
    SCHEDULER_IDLE,
    SUPPORTED_CAPABILITIES,
    SUPPORTED_PROTOCOL_VERSION,
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
    NACK_BUSY,
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
    heartbeat_timeout_s: float = 0.5
    dedupe_cache_size: int = 64
    link_state: str = LINK_DISCONNECTED
    protocol_synced: bool = False
    negotiated_capabilities: frozenset[str] = field(default_factory=frozenset)
    _recent_results: dict[str, str] = field(default_factory=dict)
    _recent_msg_ids: list[str] = field(default_factory=list)
    _last_heartbeat_at: float | None = None

    def handle_frame(self, frame: str) -> str:
        self._refresh_link_state(time.monotonic())
        try:
            packet = parse_frame(frame)
        except FrameFormatError:
            return self._nack(NACK_MALFORMED_FRAME, DETAIL_MALFORMED_FRAME, msg_id="0")

        if packet.msg_id in self._recent_results:
            return self._recent_results[packet.msg_id]

        cmd = packet.command
        args = packet.args
        if self.busy:
            response = self._nack(*CANONICAL_NACK_7, msg_id=packet.msg_id)
            self._remember(packet.msg_id, response)
            return response
        if cmd == CMD_HELLO:
            response = self._hello(args, packet.msg_id)
            self._remember(packet.msg_id, response)
            return response
        if cmd == CMD_HEARTBEAT:
            response = self._heartbeat(args, packet.msg_id)
            self._remember(packet.msg_id, response)
            return response
        if cmd == CMD_SET_MODE:
            response = self._set_mode(args, packet.msg_id)
            self._remember(packet.msg_id, response)
            return response
        if cmd == CMD_SCHED:
            response = self._sched(args, packet.msg_id)
            self._remember(packet.msg_id, response)
            return response
        if cmd == CMD_GET_STATE:
            if args:
                response = self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH, msg_id=packet.msg_id)
                self._remember(packet.msg_id, response)
                return response
            response = self._ack(False, packet.msg_id)
            self._remember(packet.msg_id, response)
            return response
        if cmd == CMD_RESET_QUEUE:
            if args:
                response = self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH, msg_id=packet.msg_id)
                self._remember(packet.msg_id, response)
                return response
            queue_cleared = bool(self.queue)
            self.queue.clear()
            self.scheduler_state = SCHEDULER_IDLE
            response = self._ack(queue_cleared, packet.msg_id)
            self._remember(packet.msg_id, response)
            return response
        response = self._nack(NACK_UNKNOWN_COMMAND, DETAIL_UNKNOWN_COMMAND, msg_id=packet.msg_id)
        self._remember(packet.msg_id, response)
        return response

    def _hello(self, args: tuple[str, ...], msg_id: str) -> str:
        if len(args) != 2:
            return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH, msg_id=msg_id)
        version = args[0]
        capabilities = {cap.strip().upper() for cap in args[1].split(";") if cap.strip()}
        if version != SUPPORTED_PROTOCOL_VERSION:
            return self._nack(NACK_ARG_RANGE_ERROR, DETAIL_ARG_RANGE_ERROR, msg_id=msg_id)
        if not capabilities:
            return self._nack(NACK_ARG_TYPE_ERROR, DETAIL_ARG_TYPE_ERROR, msg_id=msg_id)
        self.protocol_synced = True
        self.negotiated_capabilities = frozenset(capabilities.intersection(SUPPORTED_CAPABILITIES))
        self.link_state = LINK_SYNCING
        return self._ack(False, msg_id)

    def _heartbeat(self, args: tuple[str, ...], msg_id: str) -> str:
        if args:
            return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH, msg_id=msg_id)
        if not self.protocol_synced:
            return self._nack(NACK_INVALID_MODE_TRANSITION, DETAIL_INVALID_MODE_TRANSITION, msg_id=msg_id)
        self._last_heartbeat_at = time.monotonic()
        self.link_state = LINK_READY
        return self._ack(False, msg_id)

    def _set_mode(self, args: tuple[str, ...], msg_id: str) -> str:
        if len(args) != 1:
            return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH, msg_id=msg_id)
        target_mode = args[0].upper()
        if target_mode not in ALLOWED_MODES:
            return self._nack(NACK_ARG_TYPE_ERROR, DETAIL_ARG_TYPE_ERROR, msg_id=msg_id)
        if not is_mode_transition_allowed(self.mode, target_mode):
            return self._nack(NACK_INVALID_MODE_TRANSITION, DETAIL_INVALID_MODE_TRANSITION, msg_id=msg_id)

        queue_cleared = False
        if target_mode == "SAFE" or target_mode != self.mode:
            queue_cleared = bool(self.queue)
            self.queue.clear()
            self.scheduler_state = SCHEDULER_IDLE
        if target_mode != self.mode:
            self.mode = target_mode
        return self._ack(queue_cleared, msg_id)

    def _sched(self, args: tuple[str, ...], msg_id: str) -> str:
        if not self.protocol_synced:
            return self._nack(NACK_INVALID_MODE_TRANSITION, DETAIL_INVALID_MODE_TRANSITION, msg_id=msg_id)
        if self.link_state in {LINK_DISCONNECTED, LINK_SYNCING}:
            return self._nack(*CANONICAL_NACK_7, msg_id=msg_id)
        if len(args) != 2:
            return self._nack(NACK_ARG_COUNT_MISMATCH, DETAIL_ARG_COUNT_MISMATCH, msg_id=msg_id)
        try:
            lane = int(args[0])
        except ValueError:
            return self._nack(NACK_ARG_TYPE_ERROR, DETAIL_ARG_TYPE_ERROR, msg_id=msg_id)
        try:
            trigger_mm = float(args[1])
        except ValueError:
            return self._nack(NACK_ARG_TYPE_ERROR, DETAIL_ARG_TYPE_ERROR, msg_id=msg_id)

        if lane < LANE_MIN or lane > LANE_MAX:
            return self._nack(NACK_ARG_RANGE_ERROR, DETAIL_ARG_RANGE_ERROR, msg_id=msg_id)
        if trigger_mm < TRIGGER_MM_MIN or trigger_mm > TRIGGER_MM_MAX:
            return self._nack(NACK_ARG_RANGE_ERROR, DETAIL_ARG_RANGE_ERROR, msg_id=msg_id)
        if len(self.queue) >= self.max_queue_depth:
            return self._nack(NACK_QUEUE_FULL, DETAIL_QUEUE_FULL, msg_id=msg_id)

        self.queue.append((lane, trigger_mm))
        self.scheduler_state = SCHEDULER_ACTIVE
        return self._ack(False, msg_id)

    def _ack(self, queue_cleared: bool, msg_id: str) -> str:
        return serialize_packet(
            ACK_TOKEN,
            (
                self.mode,
                str(len(self.queue)),
                self.scheduler_state,
                str(queue_cleared).lower(),
                self.link_state,
            ),
            msg_id=msg_id,
        )

    @staticmethod
    def _nack(code: int, detail: str, *, msg_id: str) -> str:
        return serialize_packet("NACK", (str(code), detail), msg_id=msg_id)

    def _remember(self, msg_id: str, response: str) -> None:
        self._recent_results[msg_id] = response
        self._recent_msg_ids.append(msg_id)
        if len(self._recent_msg_ids) > self.dedupe_cache_size:
            evicted = self._recent_msg_ids.pop(0)
            self._recent_results.pop(evicted, None)

    def _refresh_link_state(self, now_s: float) -> None:
        if not self.protocol_synced:
            self.link_state = LINK_DISCONNECTED
            return
        if self._last_heartbeat_at is None:
            self.link_state = LINK_SYNCING
            return
        if now_s - self._last_heartbeat_at > self.heartbeat_timeout_s:
            self.link_state = LINK_DEGRADED
        else:
            self.link_state = LINK_READY
