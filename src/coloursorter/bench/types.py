from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BenchMode(str, Enum):
    REPLAY = "replay"
    LIVE = "live"


class FaultState(str, Enum):
    NORMAL = "normal"
    SAFE = "safe"
    WATCHDOG = "watchdog"


class AckCode(str, Enum):
    ACK = "ACK"
    NACK_QUEUE_FULL = "NACK_QUEUE_FULL"
    NACK_SAFE = "NACK_SAFE"
    NACK_WATCHDOG = "NACK_WATCHDOG"


@dataclass(frozen=True)
class BenchFrame:
    frame_id: int
    timestamp_s: float
    image_bgr: object


@dataclass(frozen=True)
class TriggerEvent:
    frame_id: int
    trigger_time_s: float
    lane: int
    decision: str
    rejection_reason: str | None


@dataclass(frozen=True)
class TransportResponse:
    ack_code: AckCode
    queue_depth: int
    round_trip_ms: float
    fault_state: FaultState = FaultState.NORMAL


@dataclass(frozen=True)
class BenchLogEntry:
    frame_timestamp_s: float
    trigger_generation_s: float
    lane: int
    decision: str
    rejection_reason: str | None
    protocol_round_trip_ms: float
    ack_code: AckCode
