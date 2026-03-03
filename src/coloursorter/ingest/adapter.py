from __future__ import annotations

from dataclasses import dataclass
import math
import json
from pathlib import Path
from typing import Any

from coloursorter.model import FrameMetadata, ObjectDetection


class IngestValidationError(ValueError):
    """Raised when inbound ingest payloads do not satisfy contract/schema."""


@dataclass(frozen=True)
class IngestCycleInput:
    frame: FrameMetadata
    detections: tuple[ObjectDetection, ...]
    previous_timestamp_s: float
    run_id: str = "default-run"
    test_batch_id: str = "default-batch"
    frame_snapshot_path: str = ""
    ground_truth_by_object_id: dict[str, str] | None = None
    captured_monotonic_s: float = 0.0
    enqueued_monotonic_s: float = 0.0
    detect_latency_ms: float = 0.0
    detection_provider_version: str = ""
    detection_model_version: str = ""
    active_config_hash: str = ""
    preprocess_metrics: dict[str, float | bool] | None = None


class IngestPayloadAdapter:
    def __init__(self, contract_path: str | Path) -> None:
        self._contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))

    def adapt(self, payload: dict[str, Any]) -> IngestCycleInput:
        self._validate_against_contract(payload)
        frame = FrameMetadata(
            frame_id=int(payload["frame_id"]),
            timestamp_s=float(payload["timestamp"]),
            image_height_px=int(payload["image_shape"][0]),
            image_width_px=int(payload["image_shape"][1]),
        )
        detections = tuple(payload.get("detections", ()))
        for detection in detections:
            if not isinstance(detection, ObjectDetection):
                raise IngestValidationError("detections must contain ObjectDetection objects")
        return IngestCycleInput(
            frame=frame,
            detections=detections,
            previous_timestamp_s=float(payload.get("previous_timestamp_s", 0.0)),
            run_id=str(payload.get("run_id", "default-run")),
            test_batch_id=str(payload.get("test_batch_id", "default-batch")),
            frame_snapshot_path=str(payload.get("frame_snapshot_path", "")),
            ground_truth_by_object_id=payload.get("ground_truth_by_object_id"),
            captured_monotonic_s=float(payload.get("captured_monotonic_s", 0.0)),
            detect_latency_ms=float(payload.get("detect_latency_ms", 0.0)),
            detection_provider_version=str(payload.get("detection_provider_version", "")),
            detection_model_version=str(payload.get("detection_model_version", "")),
            active_config_hash=str(payload.get("active_config_hash", "")),
            preprocess_metrics=payload.get("preprocess_metrics"),
        )

    def _validate_against_contract(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise IngestValidationError("payload must be a mapping")

        ingest_required = {"frame_id", "timestamp", "image_shape"}
        required = tuple(self._contract.get("required", ()))
        # Some hardening artifacts now share a wire-frame schema path that is not
        # compatible with bench ingest payloads. Keep ingest validation deterministic
        # by enforcing ingest keys directly and only honoring compatible contract keys.
        contract_required = tuple(key for key in required if key in ingest_required)
        for key in contract_required:
            if key not in payload:
                raise IngestValidationError(f"Missing required field: {key}")

        for key in ingest_required:
            if key not in payload:
                raise IngestValidationError(f"Missing required field: {key}")

        frame_id = payload.get("frame_id")
        if isinstance(frame_id, bool) or not isinstance(frame_id, int):
            raise IngestValidationError("frame_id must be integer")

        if frame_id < 0:
            raise IngestValidationError("frame_id must be >= 0")

        timestamp = payload.get("timestamp")
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise IngestValidationError("timestamp must be number")
        if not math.isfinite(float(timestamp)):
            raise IngestValidationError("timestamp must be finite")
        if float(timestamp) < 0.0:
            raise IngestValidationError("timestamp must be >= 0")

        image_shape = payload.get("image_shape")
        if (
            not isinstance(image_shape, list)
            or len(image_shape) != 3
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in image_shape)
        ):
            raise IngestValidationError("image_shape must be integer triplet [height, width, channels]")

        height_px, width_px, channels = image_shape
        if height_px <= 0 or width_px <= 0:
            raise IngestValidationError("image_shape height and width must be > 0")
        if channels not in {1, 3, 4}:
            raise IngestValidationError("image_shape channels must be one of: 1, 3, 4")

        previous_timestamp_s = payload.get("previous_timestamp_s", 0.0)
        if isinstance(previous_timestamp_s, bool) or not isinstance(previous_timestamp_s, (int, float)):
            raise IngestValidationError("previous_timestamp_s must be number")
        if not math.isfinite(float(previous_timestamp_s)):
            raise IngestValidationError("previous_timestamp_s must be finite")
        if float(previous_timestamp_s) < 0.0:
            raise IngestValidationError("previous_timestamp_s must be >= 0")
        if float(previous_timestamp_s) > float(timestamp):
            raise IngestValidationError("previous_timestamp_s must be <= timestamp")
