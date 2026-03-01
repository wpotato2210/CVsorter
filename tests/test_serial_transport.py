from __future__ import annotations

import pytest

from coloursorter.bench.serial_transport import (
    SerialMcuTransport,
    SerialTransportConfig,
    SerialTransportError,
)
from coloursorter.bench.types import AckCode, FaultState
from coloursorter.scheduler import ScheduledCommand


class _FakeSerial:
    def __init__(self, response: bytes | list[bytes]) -> None:
        self._response = response
        self.written: bytes | None = None

    def write(self, payload: bytes) -> None:
        self.written = payload

    def readline(self) -> bytes:
        if isinstance(self._response, list):
            return self._response.pop(0) if self._response else b""
        return self._response

    def close(self) -> None:
        return None


def test_serial_transport_encodes_sched_and_parses_ack() -> None:
    fake = _FakeSerial(b"<ACK|AUTO|1|ACTIVE|false>\n")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=1, position_mm=200.0))

    assert fake.written == b"<SCHED|1|200.000>\n"
    assert response.ack_code == AckCode.ACK
    assert response.queue_depth == 1
    assert response.scheduler_state == "ACTIVE"
    assert response.mode == "AUTO"
    assert response.fault_state == FaultState.NORMAL
    assert transport.current_fault_state() == FaultState.NORMAL


def test_serial_transport_maps_nack_busy() -> None:
    fake = _FakeSerial(b"<NACK|7|BUSY>\n")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=2, position_mm=250.0))

    assert response.ack_code == AckCode.NACK_BUSY
    assert response.fault_state == FaultState.NORMAL
    assert response.nack_code == 7
    assert response.nack_detail == "BUSY"


def test_serial_transport_treats_noncanonical_nack_code_7_watchdog_as_safe() -> None:
    fake = _FakeSerial(b"<NACK|7|WATCHDOG>\n")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=2, position_mm=250.0))

    assert response.ack_code == AckCode.NACK_SAFE
    assert response.fault_state == FaultState.SAFE
    assert response.nack_code == 7
    assert response.nack_detail == "WATCHDOG"

@pytest.mark.parametrize(
    ("raw_response", "expected_ack", "expected_fault"),
    [
        (b"<ACK>\n", AckCode.ACK, FaultState.NORMAL),
        (b"<NACK|6|QUEUE_FULL>\n", AckCode.NACK_QUEUE_FULL, FaultState.NORMAL),
        (b"<NACK|5|SAFE>\n", AckCode.NACK_SAFE, FaultState.SAFE),
        (b"<NACK|7|BUSY>\n", AckCode.NACK_BUSY, FaultState.NORMAL),
    ],
)
def test_serial_transport_contract_ack_nack_mapping(
    raw_response: bytes,
    expected_ack: AckCode,
    expected_fault: FaultState,
) -> None:
    fake = _FakeSerial(raw_response)
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=1, position_mm=210.0))

    assert response.ack_code == expected_ack
    assert response.fault_state == expected_fault


def test_serial_transport_maps_canonical_watchdog_without_nack_code() -> None:
    from coloursorter.bench.serial_transport import _map_ack_to_bench_state

    ack_code, fault_state = _map_ack_to_bench_state("NACK", None, "WATCHDOG")

    assert ack_code == AckCode.NACK_WATCHDOG
    assert fault_state == FaultState.WATCHDOG

def test_serial_transport_raises_structured_timeout_error() -> None:
    fake = _FakeSerial(b"")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    with pytest.raises(SerialTransportError) as exc_info:
        transport.send(ScheduledCommand(lane=3, position_mm=111.0))

    assert exc_info.value.category == "serial_timeout"
    assert "No MCU response within" in exc_info.value.detail
    assert exc_info.value.fault_state == FaultState.WATCHDOG
    assert exc_info.value.telemetry.category == "serial_timeout"
    assert exc_info.value.telemetry.fault_state == FaultState.WATCHDOG


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


def test_serial_transport_updates_current_fault_state_on_nack() -> None:
    fake = _FakeSerial(b"<NACK|5|SAFE>\n")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=2, position_mm=250.0))

    assert response.fault_state == FaultState.SAFE
    assert transport.current_fault_state() == FaultState.SAFE


def test_serial_transport_retries_on_timeout_then_succeeds() -> None:
    fake = _FakeSerial([b"", b"<ACK|AUTO|1|ACTIVE|false>\n"])
    slept: list[float] = []
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
        sleep_fn=lambda s: slept.append(s),
    )

    response = transport.send(ScheduledCommand(lane=1, position_mm=200.0))

    assert response.ack_code == AckCode.ACK
    assert slept == [0.0]


def test_serial_transport_exhausts_retries_before_timeout_error() -> None:
    fake = _FakeSerial([b"", b"", b"", b""])
    slept: list[float] = []
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
        sleep_fn=lambda s: slept.append(s),
    )

    with pytest.raises(SerialTransportError) as exc_info:
        transport.send(ScheduledCommand(lane=3, position_mm=111.0))

    assert exc_info.value.category == "serial_timeout"
    assert slept == [0.0, 0.05, 0.1]


def test_serial_transport_preserves_raw_nack_detail() -> None:
    fake = _FakeSerial(b"<NACK|6|QUEUE_FULL>\n")
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=2, position_mm=250.0))

    assert response.ack_code == AckCode.NACK_QUEUE_FULL
    assert response.nack_code == 6
    assert response.nack_detail == "QUEUE_FULL"
