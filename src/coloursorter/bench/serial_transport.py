from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from coloursorter.scheduler import ScheduledCommand
from coloursorter.protocol.constants import (
    CMD_HEARTBEAT,
    CMD_HELLO,
    CMD_SCHED,
    SUPPORTED_CAPABILITIES,
    SUPPORTED_PROTOCOL_VERSION,
)
from coloursorter.protocol.nack_codes import (
    CANONICAL_NACK_7,
    DETAIL_SAFE,
    DETAIL_WATCHDOG,
    NACK_INVALID_MODE_TRANSITION,
    NACK_QUEUE_FULL,
    is_canonical_nack,
)

from coloursorter.serial_interface import (
    AckResponse,
    FrameFormatError,
    PacketValidationError,
    decode_packet_bytes,
    encode_packet_bytes,
    parse_ack_tokens,
)

from .types import AckCode, FaultState, TransportResponse


@dataclass(frozen=True)
class SerialTransportConfig:
    port: str
    baud: int
    timeout_s: float
    ack_timeout_ms: int = 100
    max_retries: int = 3
    backoff_ms: tuple[int, ...] = (0, 50, 100)
    heartbeat_interval_s: float = 0.2
    protocol_version: str = SUPPORTED_PROTOCOL_VERSION
    capabilities: tuple[str, ...] = tuple(sorted(SUPPORTED_CAPABILITIES))


@dataclass(frozen=True)
class BenchTelemetryEntry:
    category: str
    detail: str
    fault_state: FaultState


@dataclass(frozen=True)
class SerialTransportError(RuntimeError):
    category: str
    detail: str
    fault_state: FaultState
    telemetry: BenchTelemetryEntry

    @classmethod
    def create(cls, category: str, detail: str, fault_state: FaultState) -> "SerialTransportError":
        return cls(
            category=category,
            detail=detail,
            fault_state=fault_state,
            telemetry=BenchTelemetryEntry(category=category, detail=detail, fault_state=fault_state),
        )


class SerialMcuTransport:
    def __init__(
        self,
        config: SerialTransportConfig,
        serial_factory: Callable[..., object] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._config = config
        self._serial_factory = serial_factory or _default_serial_factory
        self._serial = self._serial_factory(port=config.port, baudrate=config.baud, timeout=config.timeout_s)
        self._last_fault_state = FaultState.NORMAL
        self._last_queue_depth = 0
        self._last_queue_cleared = False
        self._sleep = sleep_fn or time.sleep
        self._next_msg_id = 1
        self._handshake_complete = False
        self._last_heartbeat_sent_at = 0.0

    def close(self) -> None:
        if hasattr(self._serial, "close"):
            self._serial.close()

    def current_fault_state(self) -> FaultState:
        return self._last_fault_state

    def current_queue_depth(self) -> int:
        return self._last_queue_depth

    def transport_queue_depth(self) -> int:
        return self._last_queue_depth

    def last_queue_cleared_observation(self) -> bool:
        return self._last_queue_cleared

    def transport_last_queue_cleared(self) -> bool:
        return self._last_queue_cleared

    def send(self, command: ScheduledCommand) -> TransportResponse:
        self._ensure_link_ready()
        ack, round_trip_ms = self._send_frame(CMD_SCHED, (command.lane, f"{command.position_mm:.3f}"))

        ack_code, fault_state = _map_ack_to_bench_state(ack.status, ack.nack_code, ack.detail)
        self._last_fault_state = fault_state
        self._last_queue_depth = ack.queue_depth or 0
        self._last_queue_cleared = ack.queue_cleared
        return TransportResponse(
            ack_code=ack_code,
            queue_depth=self._last_queue_depth,
            round_trip_ms=round_trip_ms,
            fault_state=fault_state,
            scheduler_state=ack.scheduler_state or "UNKNOWN",
            mode=ack.mode or "UNKNOWN",
            queue_cleared=self._last_queue_cleared,
            nack_code=ack.nack_code,
            nack_detail=ack.detail,
        )

    def send_command(self, command: str, args: tuple[object, ...] = ()) -> AckResponse:
        self._ensure_link_ready()
        ack, _ = self._send_frame(command, args)
        return ack

    def _send_frame(self, command: str, args: tuple[object, ...] = ()) -> tuple[AckResponse, float]:
        msg_id = self._reserve_msg_id()
        payload = encode_packet_bytes(command, args, msg_id=msg_id)

        for attempt in range(self._config.max_retries + 1):
            started = time.perf_counter()
            self._serial.write(payload)
            raw_response = self._serial.readline()
            round_trip_ms = (time.perf_counter() - started) * 1000.0

            if not raw_response:
                if attempt < self._config.max_retries:
                    self._sleep(self._backoff_for_attempt(attempt) / 1000.0)
                    continue
                self._last_fault_state = FaultState.WATCHDOG
                raise SerialTransportError.create(
                    category="serial_timeout",
                    detail=f"No MCU response within {self._config.timeout_s:.3f}s",
                    fault_state=FaultState.WATCHDOG,
                )

            try:
                parsed = decode_packet_bytes(raw_response)
                ack = parse_ack_tokens((parsed.command, *parsed.args))
            except (FrameFormatError, PacketValidationError) as exc:
                self._last_fault_state = FaultState.SAFE
                raise SerialTransportError.create(
                    category="serial_parse_error",
                    detail=str(exc),
                    fault_state=FaultState.SAFE,
                ) from exc

            self._last_queue_depth = ack.queue_depth or 0
            self._last_queue_cleared = ack.queue_cleared
            return ack, round_trip_ms

        raise AssertionError("unreachable")

    def _ensure_link_ready(self) -> None:
        now = time.monotonic()
        if not self._handshake_complete:
            caps = ";".join(self._config.capabilities)
            self._send_frame(CMD_HELLO, (self._config.protocol_version, caps))
            self._handshake_complete = True
            self._last_heartbeat_sent_at = 0.0
        if now - self._last_heartbeat_sent_at >= self._config.heartbeat_interval_s:
            self._send_frame(CMD_HEARTBEAT)
            self._last_heartbeat_sent_at = now

    def _reserve_msg_id(self) -> str:
        msg_id = str(self._next_msg_id)
        self._next_msg_id += 1
        return msg_id

    def _backoff_for_attempt(self, attempt: int) -> int:
        if attempt < len(self._config.backoff_ms):
            return self._config.backoff_ms[attempt]
        return self._config.backoff_ms[-1] if self._config.backoff_ms else 0


def _map_ack_to_bench_state(status: str, nack_code: int | None, detail: str | None) -> tuple[AckCode, FaultState]:
    if status == "ACK":
        return AckCode.ACK, FaultState.NORMAL

    normalized_detail = (detail or "").strip().upper()
    if is_canonical_nack(nack_code, normalized_detail) and nack_code == NACK_QUEUE_FULL:
        return AckCode.NACK_QUEUE_FULL, FaultState.NORMAL
    if is_canonical_nack(nack_code, normalized_detail) and nack_code == NACK_INVALID_MODE_TRANSITION:
        return AckCode.NACK_SAFE, FaultState.SAFE
    if nack_code == NACK_INVALID_MODE_TRANSITION and normalized_detail == DETAIL_SAFE:
        return AckCode.NACK_SAFE, FaultState.SAFE
    if is_canonical_nack(nack_code, normalized_detail) and (nack_code, normalized_detail) == CANONICAL_NACK_7:
        return AckCode.NACK_BUSY, FaultState.NORMAL
    if nack_code is None and normalized_detail == DETAIL_WATCHDOG:
        return AckCode.NACK_WATCHDOG, FaultState.WATCHDOG
    return AckCode.NACK_SAFE, FaultState.SAFE


def _default_serial_factory(**kwargs: object) -> object:
    try:
        import serial  # type: ignore
    except ImportError as exc:  # pragma: no cover - only used when pyserial missing in runtime
        raise RuntimeError("pyserial is required for SerialMcuTransport") from exc
    return serial.Serial(**kwargs)
