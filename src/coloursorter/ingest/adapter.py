from __future__ import annotations

from dataclasses import dataclass
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
        )

    def _validate_against_contract(self, payload: dict[str, Any]) -> None:
        required = tuple(self._contract.get("required", ()))
        for key in required:
            if key not in payload:
                raise IngestValidationError(f"Missing required field: {key}")

        if not isinstance(payload.get("frame_id"), int):
            raise IngestValidationError("frame_id must be integer")
        if not isinstance(payload.get("timestamp"), (int, float)):
            raise IngestValidationError("timestamp must be number")

        image_shape = payload.get("image_shape")
        if not isinstance(image_shape, list) or len(image_shape) != 3 or not all(isinstance(v, int) for v in image_shape):
            raise IngestValidationError("image_shape must be integer triplet [height, width, channels]")
