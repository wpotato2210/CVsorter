from __future__ import annotations

from typing import Callable

from coloursorter.scheduler import ScheduledCommand

from .serial_transport import SerialMcuTransport, SerialTransportConfig
from .types import FaultState, TransportResponse


class Esp32McuTransport:
    """ESP32 transport adapter backed by serial wire protocol behavior."""

    def __init__(
        self,
        config: SerialTransportConfig,
        serial_factory: Callable[..., object] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._serial_transport = SerialMcuTransport(
            config=config,
            serial_factory=serial_factory,
            sleep_fn=sleep_fn,
        )

    def close(self) -> None:
        self._serial_transport.close()

    def send(self, command: ScheduledCommand) -> TransportResponse:
        return self._serial_transport.send(command)

    def send_command(self, command: str, args: tuple[object, ...] = ()):
        return self._serial_transport.send_command(command, args)

    def current_fault_state(self) -> FaultState:
        return self._serial_transport.current_fault_state()

    def current_queue_depth(self) -> int:
        return self._serial_transport.current_queue_depth()

    def transport_queue_depth(self) -> int:
        return self._serial_transport.transport_queue_depth()

    def last_queue_cleared_observation(self) -> bool:
        return self._serial_transport.last_queue_cleared_observation()

    def transport_last_queue_cleared(self) -> bool:
        return self._serial_transport.transport_last_queue_cleared()
