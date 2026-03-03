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
    NACK_BUSY = "NACK_BUSY"
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
    scheduler_state: str = "IDLE"
    mode: str = "AUTO"
    queue_cleared: bool = False
    nack_code: int | None = None
    nack_detail: str | None = None


@dataclass(frozen=True)
class BenchLogEntry:
    frame_timestamp_s: float
    trigger_generation_s: float
    lane: int
    decision: str
    rejection_reason: str | None
    protocol_round_trip_ms: float
    ack_code: AckCode | str
    trigger_timestamp_s: float = 0.0
    trigger_mm: float = 0.0
    lane_index: int = -1
    belt_speed_mm_s: float = 0.0
    queue_depth: int = 0
    scheduler_state: str = "IDLE"
    mode: str = "AUTO"
    queue_cleared: bool = False
    ingest_latency_ms: float = 0.0
    decision_latency_ms: float = 0.0
    schedule_latency_ms: float = 0.0
    transport_latency_ms: float = 0.0
    cycle_latency_ms: float = 0.0
    detect_latency_ms: float = 0.0
    queue_age_ms: float = 0.0
    frame_staleness_ms: float = 0.0
    total_budget_ms: float = 0.0
    over_budget: bool = False
    fault_event: str = ""
    timebase_reference: str = "encoder_epoch"
    trigger_reference_s: float = 0.0
    rtt_jitter_ms: float = 0.0
    jitter_warn: bool = False
    jitter_critical: bool = False
    nack_code: int | None = None
    nack_detail: str | None = None
    run_id: str = "default-run"
    test_batch_id: str = "default-batch"
    event_timestamp_utc: str = ""
    frame_id: int = -1
    object_id: str = ""
    prediction_label: str = ""
    confidence: float = 0.0
    actuator_command_issued: bool = False
    actuator_command_payload: str = ""
    command_source: str = ""
    frame_snapshot_path: str = ""
    ground_truth_label: str = ""
    decision_reason: str = ""
    detection_provider_version: str = ""
    detection_model_version: str = ""
    active_config_hash: str = ""
    preprocess_valid: bool = True
    preprocess_luma_before: float = 0.0
    preprocess_luma_after: float = 0.0
    preprocess_exposure_gain: float = 1.0
    preprocess_wb_gain_b: float = 1.0
    preprocess_wb_gain_g: float = 1.0
    preprocess_wb_gain_r: float = 1.0
    preprocess_clipped_ratio: float = 0.0
