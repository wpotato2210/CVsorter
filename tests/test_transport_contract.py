from __future__ import annotations

from typing import cast

from coloursorter.bench.esp32_transport import Esp32McuTransport
from coloursorter.bench.mock_transport import MockMcuTransport, MockTransportConfig
from coloursorter.bench.serial_transport import SerialTransportConfig
from coloursorter.bench.transport import McuTransport
from coloursorter.bench.types import FaultState


def test_mock_transport_current_fault_state_reflects_configured_state() -> None:
    transport = MockMcuTransport(
        config=MockTransportConfig(max_queue_depth=4, base_round_trip_ms=1.0, per_item_penalty_ms=0.5),
        fault_state=FaultState.SAFE,
    )

    assert transport.current_fault_state() == FaultState.SAFE


class _FakeSerial:
    def write(self, _payload: bytes) -> None:
        return None

    def readline(self) -> bytes:
        return b"<ACK|AUTO|0|IDLE|false>\n"


def test_esp32_transport_conforms_to_mcu_transport_contract() -> None:
    transport = Esp32McuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: _FakeSerial(),
    )

    contract = cast(McuTransport, transport)

    assert contract.current_fault_state() == FaultState.NORMAL
    assert contract.current_queue_depth() == 0
    assert contract.last_queue_cleared_observation() is False
