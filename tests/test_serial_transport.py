from __future__ import annotations

import pytest

from coloursorter.bench.esp32_transport import Esp32McuTransport
from coloursorter.bench.serial_transport import (
    SerialMcuTransport,
    SerialTransportConfig,
    SerialTransportError,
    _map_ack_to_bench_state,
)
from coloursorter.bench.types import AckCode, FaultState
from coloursorter.protocol import OpenSpecV3Host
from coloursorter.protocol.nack_codes import CANONICAL_NACK_7, DETAIL_BUSY, DETAIL_WATCHDOG, NACK_BUSY
from coloursorter.scheduler import ScheduledCommand
from coloursorter.serial_interface import parse_frame, serialize_packet


class _HostBackedSerial:
    def __init__(self, host: OpenSpecV3Host) -> None:
        self._host = host
        self.written: list[bytes] = []

    def write(self, payload: bytes) -> None:
        self.written.append(payload)

    def readline(self) -> bytes:
        request = self.written[-1].decode().strip()
        return self._host.handle_frame(request).encode() + b"\n"

    def close(self) -> None:
        return None


def test_serial_transport_encodes_sched_and_parses_ack() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    fake = _HostBackedSerial(host)
    transport = SerialMcuTransport(SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05), serial_factory=lambda **_: fake)

    response = transport.send(ScheduledCommand(lane=1, position_mm=200.0))

    assert parse_frame(fake.written[-1].decode().strip()).command == "SCHED"
    assert response.ack_code == AckCode.ACK
    assert response.scheduler_state == "ACTIVE"


def test_serial_transport_deduplicates_replayed_msg_id_on_host() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    first = host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="8"))
    assert "ACK" in first
    host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="9"))
    before = len(host.queue)
    frame = serialize_packet("SCHED", (1, "100.000"), msg_id="11")

    host.handle_frame(frame)
    host.handle_frame(frame)

    assert len(host.queue) == before + 1


@pytest.mark.parametrize(
    ("status", "code", "detail", "expected_ack", "expected_fault"),
    [
        ("ACK", None, None, AckCode.ACK, FaultState.NORMAL),
        ("NACK", 6, "QUEUE_FULL", AckCode.NACK_QUEUE_FULL, FaultState.NORMAL),
        ("NACK", 5, "SAFE", AckCode.NACK_SAFE, FaultState.SAFE),
        ("NACK", NACK_BUSY, DETAIL_BUSY, AckCode.NACK_BUSY, FaultState.NORMAL),
    ],
)
def test_serial_transport_contract_ack_nack_mapping(status: str, code: int | None, detail: str | None, expected_ack: AckCode, expected_fault: FaultState) -> None:
    ack_code, fault = _map_ack_to_bench_state(status, code, detail)
    assert ack_code == expected_ack
    assert fault == expected_fault


def test_serial_transport_maps_canonical_busy_pair_to_busy_state() -> None:
    code, detail = CANONICAL_NACK_7
    ack_code, fault_state = _map_ack_to_bench_state("NACK", code, detail)
    assert ack_code == AckCode.NACK_BUSY
    assert fault_state == FaultState.NORMAL


def test_serial_transport_maps_canonical_watchdog_without_nack_code() -> None:
    ack_code, fault_state = _map_ack_to_bench_state("NACK", None, DETAIL_WATCHDOG)
    assert ack_code == AckCode.NACK_WATCHDOG
    assert fault_state == FaultState.WATCHDOG


def test_serial_transport_raises_structured_timeout_error() -> None:
    class _TimeoutSerial:
        def write(self, _payload: bytes) -> None:
            return None

        def readline(self) -> bytes:
            return b""

    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: _TimeoutSerial(),
    )

    with pytest.raises(SerialTransportError) as exc_info:
        transport.send(ScheduledCommand(lane=3, position_mm=111.0))

    assert exc_info.value.category == "serial_timeout"


@pytest.mark.parametrize("transport_cls", [SerialMcuTransport, Esp32McuTransport])
def test_esp32_adapter_matches_serial_sched_path(transport_cls: type[SerialMcuTransport] | type[Esp32McuTransport]) -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    fake = _HostBackedSerial(host)
    transport = transport_cls(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=1, position_mm=200.0))

    assert parse_frame(fake.written[-1].decode().strip()).command == "SCHED"
    assert response.ack_code == AckCode.ACK
