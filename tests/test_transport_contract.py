from __future__ import annotations

from coloursorter.bench.mock_transport import MockMcuTransport, MockTransportConfig
from coloursorter.bench.types import FaultState


def test_mock_transport_current_fault_state_reflects_configured_state() -> None:
    transport = MockMcuTransport(
        config=MockTransportConfig(max_queue_depth=4, base_round_trip_ms=1.0, per_item_penalty_ms=0.5),
        fault_state=FaultState.SAFE,
    )

    assert transport.current_fault_state() == FaultState.SAFE
