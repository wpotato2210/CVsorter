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
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05, heartbeat_interval_s=0.0),
        serial_factory=lambda **_: _TimeoutSerial(),
    )

    with pytest.raises(SerialTransportError) as exc_info:
        transport.send(ScheduledCommand(lane=3, position_mm=111.0))

    assert exc_info.value.category == "serial_timeout"


def test_serial_transport_requires_get_state_sync_and_recovers_with_reset_and_mode_set() -> None:
    host = OpenSpecV3Host(max_queue_depth=4, mode="MANUAL")
    host.queue.append((1, 123.0))
    host.scheduler_state = "ACTIVE"
    fake = _HostBackedSerial(host)
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05, heartbeat_interval_s=0.0),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=1, position_mm=200.0))

    commands = [parse_frame(raw.decode().strip()).command for raw in fake.written]
    assert commands[:6] == ["HELLO", "HEARTBEAT", "GET_STATE", "RESET_QUEUE", "SET_MODE", "SCHED"]
    assert response.ack_code == AckCode.ACK
    assert response.mode == "AUTO"
    assert response.queue_depth == 1


def test_serial_transport_marks_in_flight_uncertain_on_timeout() -> None:
    class _TimeoutSerial:
        def write(self, _payload: bytes) -> None:
            return None

        def readline(self) -> bytes:
            return b""

    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.01, max_retries=0),
        serial_factory=lambda **_: _TimeoutSerial(),
    )

    with pytest.raises(SerialTransportError):
        transport.send(ScheduledCommand(lane=3, position_mm=111.0))

    metadata = transport.last_in_flight_command()
    assert metadata is not None
    assert metadata.uncertain_outcome is True
    assert metadata.uncertainty_reason == "NO_RESPONSE"


def test_fault_injection_cable_unplug_replug_requires_resync() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)

    class _FlakySerial(_HostBackedSerial):
        def __init__(self, mcu_host: OpenSpecV3Host) -> None:
            super().__init__(mcu_host)
            self._drop_once = True

        def readline(self) -> bytes:
            request = self.written[-1].decode().strip()
            command = parse_frame(request).command
            if command == "HEARTBEAT" and self._drop_once:
                self._drop_once = False
                return b""
            return self._host.handle_frame(request).encode() + b"\n"

    fake = _FlakySerial(host)
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.01, max_retries=0, heartbeat_interval_s=0.0),
        serial_factory=lambda **_: fake,
    )

    with pytest.raises(SerialTransportError):
        transport.send(ScheduledCommand(lane=1, position_mm=50.0))

    response = transport.send(ScheduledCommand(lane=1, position_mm=51.0))
    commands = [parse_frame(raw.decode().strip()).command for raw in fake.written]
    assert "GET_STATE" in commands
    assert response.ack_code == AckCode.ACK


def test_fault_injection_mcu_reset_mid_queue_triggers_deterministic_recovery() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    fake = _HostBackedSerial(host)
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05, heartbeat_interval_s=0.0),
        serial_factory=lambda **_: fake,
    )

    first = transport.send(ScheduledCommand(lane=1, position_mm=80.0))
    assert first.ack_code == AckCode.ACK

    host.protocol_synced = False
    host.queue.clear()
    host.scheduler_state = "IDLE"
    host.mode = "AUTO"

    second = transport.send(ScheduledCommand(lane=1, position_mm=81.0))
    commands = [parse_frame(raw.decode().strip()).command for raw in fake.written]
    assert commands.count("HELLO") >= 2
    assert commands.count("GET_STATE") >= 2
    assert second.ack_code == AckCode.ACK


@pytest.mark.parametrize("transport_cls", [SerialMcuTransport, Esp32McuTransport])
def test_esp32_adapter_matches_serial_sched_path(transport_cls: type[SerialMcuTransport] | type[Esp32McuTransport]) -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    fake = _HostBackedSerial(host)
    transport = transport_cls(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05, heartbeat_interval_s=0.0),
        serial_factory=lambda **_: fake,
    )

    response = transport.send(ScheduledCommand(lane=1, position_mm=200.0))

    assert parse_frame(fake.written[-1].decode().strip()).command == "SCHED"
    assert response.ack_code == AckCode.ACK


def test_mock_and_serial_esp32_parity_for_identical_sched_input() -> None:
    from coloursorter.bench.mock_transport import MockMcuTransport, MockTransportConfig

    host_a = OpenSpecV3Host(max_queue_depth=4)
    host_b = OpenSpecV3Host(max_queue_depth=4)
    serial_transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05, heartbeat_interval_s=0.0),
        serial_factory=lambda **_: _HostBackedSerial(host_a),
    )
    esp32_transport = Esp32McuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05, heartbeat_interval_s=0.0),
        serial_factory=lambda **_: _HostBackedSerial(host_b),
    )
    mock_transport = MockMcuTransport(MockTransportConfig(max_queue_depth=4, base_round_trip_ms=2.0, per_item_penalty_ms=0.0))

    command = ScheduledCommand(lane=1, position_mm=200.0)
    serial_response = serial_transport.send(command)
    esp32_response = esp32_transport.send(command)
    mock_response = mock_transport.send(command)

    assert serial_response.ack_code == AckCode.ACK
    assert esp32_response.ack_code == serial_response.ack_code
    assert mock_response.ack_code == serial_response.ack_code
    assert esp32_response.queue_depth == serial_response.queue_depth
    assert mock_response.queue_depth == serial_response.queue_depth
    assert esp32_response.scheduler_state == serial_response.scheduler_state
    assert mock_response.scheduler_state == serial_response.scheduler_state


def test_serial_transport_get_state_queue_depth_drift_does_not_force_reset() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    fake = _HostBackedSerial(host)
    transport = SerialMcuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05, heartbeat_interval_s=0.0),
        serial_factory=lambda **_: fake,
    )
    transport._last_queue_depth = 3  # stale derived cache should not trigger RESET_QUEUE by itself

    transport.send(ScheduledCommand(lane=1, position_mm=200.0))

    commands = [parse_frame(raw.decode().strip()).command for raw in fake.written]
    assert "RESET_QUEUE" not in commands

