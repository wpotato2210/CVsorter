from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class RuntimeTraceEntry:
    """Deterministic per-object runtime trace record."""

    timestamp: float
    frame_id: int
    lane_id: int
    bbox: tuple[float, float, float, float]
    color_class: str
    confidence: float
    decision: str
    actuator_command: dict[str, float | int] | None
    latency_ms: float

    def to_jsonl(self) -> str:
        payload = {
            "timestamp": float(self.timestamp),
            "frame_id": int(self.frame_id),
            "lane_id": int(self.lane_id),
            "bbox": [float(value) for value in self.bbox],
            "color_class": str(self.color_class),
            "confidence": float(self.confidence),
            "decision": str(self.decision),
            "actuator_command": self.actuator_command,
            "latency_ms": float(self.latency_ms),
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


class RuntimeTraceLogger:
    def __init__(self, log_path: str | Path | None) -> None:
        self._log_path = Path(log_path) if log_path is not None else None
        self._stream: TextIO | None = None

    @property
    def enabled(self) -> bool:
        return self._log_path is not None

    def open(self) -> None:
        if self._log_path is None or self._stream is not None:
            return
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self._log_path.open("a", encoding="utf-8", buffering=1)

    def write(self, entry: RuntimeTraceEntry) -> None:
        if self._stream is None:
            return
        self._stream.write(entry.to_jsonl())
        self._stream.write("\n")

    def close(self) -> None:
        if self._stream is None:
            return
        self._stream.close()
        self._stream = None
