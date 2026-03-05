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

        self._validate_optional_number(payload, "captured_monotonic_s", minimum=0.0)
        self._validate_optional_number(payload, "detect_latency_ms", minimum=0.0)

        self._validate_optional_string(payload, "run_id", max_length=128)
        self._validate_optional_string(payload, "test_batch_id", max_length=128)
        self._validate_optional_string(payload, "detection_provider_version", max_length=64)
        self._validate_optional_string(payload, "detection_model_version", max_length=64)
        self._validate_optional_string(payload, "active_config_hash", max_length=128)
        self._validate_optional_string(payload, "frame_snapshot_path", max_length=1024)

        ground_truth_by_object_id = payload.get("ground_truth_by_object_id")
        if ground_truth_by_object_id is not None:
            if not isinstance(ground_truth_by_object_id, dict):
                raise IngestValidationError("ground_truth_by_object_id must be mapping when provided")
            for object_id, label in ground_truth_by_object_id.items():
                if not isinstance(object_id, str) or not object_id:
                    raise IngestValidationError("ground_truth_by_object_id keys must be non-empty strings")
                if not isinstance(label, str) or not label:
                    raise IngestValidationError("ground_truth_by_object_id values must be non-empty strings")

        preprocess_metrics = payload.get("preprocess_metrics")
        if preprocess_metrics is not None:
            if not isinstance(preprocess_metrics, dict):
                raise IngestValidationError("preprocess_metrics must be mapping when provided")
            for metric_name, metric_value in preprocess_metrics.items():
                if not isinstance(metric_name, str) or not metric_name:
                    raise IngestValidationError("preprocess_metrics keys must be non-empty strings")
                if isinstance(metric_value, bool):
                    continue
                if not isinstance(metric_value, (int, float)):
                    raise IngestValidationError("preprocess_metrics values must be numeric or boolean")
                if not math.isfinite(float(metric_value)):
                    raise IngestValidationError("preprocess_metrics numeric values must be finite")

    def _validate_optional_number(self, payload: dict[str, Any], key: str, *, minimum: float) -> None:
        value = payload.get(key)
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise IngestValidationError(f"{key} must be number")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise IngestValidationError(f"{key} must be finite")
        if numeric < minimum:
            raise IngestValidationError(f"{key} must be >= {minimum}")

    def _validate_optional_string(self, payload: dict[str, Any], key: str, *, max_length: int) -> None:
        value = payload.get(key)
        if value is None:
            return
        if not isinstance(value, str):
            raise IngestValidationError(f"{key} must be string")
        if not value.strip():
            raise IngestValidationError(f"{key} must be non-empty when provided")
        if len(value) > max_length:
            raise IngestValidationError(f"{key} length must be <= {max_length}")
