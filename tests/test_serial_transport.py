from __future__ import annotations

import pytest

from coloursorter.bench.serial_transport import SerialMcuTransport, SerialTransportConfig, SerialTransportError
from coloursorter.bench.types import AckCode, FaultState
from coloursorter.scheduler import ScheduledCommand


class _FakeSerial:
    def __init__(self, response: bytes) -> None:
        self._response = response
        self.written: bytes | None = None

    def write(self, payload: bytes) -> None:
        self.written = payload

    def readline(self) -> bytes:
        return self._response

    def close(self) -> None:
        return None


def test_serial_transport_encodes_sched_and_parses_ack() -> None:
    fake = _FakeSerial(b"<ACK>\n")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=1, position_mm=200.0))

    assert fake.written == b"<SCHED|1|200.000>\n"
    assert response.ack_code == AckCode.ACK
    assert response.fault_state == FaultState.NORMAL


def test_serial_transport_maps_nack_watchdog() -> None:
    fake = _FakeSerial(b"<NACK|3|WATCHDOG>\n")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=2, position_mm=250.0))

    assert response.ack_code == AckCode.NACK_WATCHDOG
    assert response.fault_state == FaultState.WATCHDOG


def test_serial_transport_raises_structured_timeout_error() -> None:
    fake = _FakeSerial(b"")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    with pytest.raises(SerialTransportError) as exc_info:
        transport.send(ScheduledCommand(lane=3, position_mm=111.0))

    assert exc_info.value.category == "serial_timeout"
    assert exc_info.value.fault_state == FaultState.WATCHDOG
    assert exc_info.value.telemetry.category == "serial_timeout"


def test_serial_transport_raises_structured_parse_error() -> None:
    fake = _FakeSerial(b"MALFORMED\n")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    with pytest.raises(SerialTransportError) as exc_info:
        transport.send(ScheduledCommand(lane=3, position_mm=111.0))

    assert exc_info.value.category == "serial_parse_error"
    assert exc_info.value.fault_state == FaultState.SAFE
    assert exc_info.value.telemetry.fault_state == FaultState.SAFE
