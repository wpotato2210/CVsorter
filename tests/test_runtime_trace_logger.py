from __future__ import annotations

import json
from pathlib import Path

from coloursorter.runtime.trace_logger import RuntimeTraceEntry, RuntimeTraceLogger


def test_runtime_trace_entry_serializes_with_deterministic_keys() -> None:
    entry = RuntimeTraceEntry(
        timestamp=123.456,
        frame_id=7,
        lane_id=2,
        bbox=(10.0, 20.0, 30.0, 40.0),
        color_class="reject",
        confidence=0.9,
        decision="reject",
        actuator_command={"lane": 2, "position_mm": 55.0},
        latency_ms=3.25,
    )

    payload = json.loads(entry.to_jsonl())

    assert payload == {
        "actuator_command": {"lane": 2, "position_mm": 55.0},
        "bbox": [10.0, 20.0, 30.0, 40.0],
        "color_class": "reject",
        "confidence": 0.9,
        "decision": "reject",
        "frame_id": 7,
        "lane_id": 2,
        "latency_ms": 3.25,
        "timestamp": 123.456,
    }
    assert entry.to_jsonl().startswith('{"actuator_command"')


def test_runtime_trace_logger_writes_jsonl_entries(tmp_path: Path) -> None:
    log_path = tmp_path / "trace" / "runtime.jsonl"
    logger = RuntimeTraceLogger(log_path)

    logger.open()
    logger.write(
        RuntimeTraceEntry(
            timestamp=1.0,
            frame_id=1,
            lane_id=0,
            bbox=(1.0, 2.0, 1.0, 2.0),
            color_class="accept",
            confidence=0.1,
            decision="accept",
            actuator_command=None,
            latency_ms=0.5,
        )
    )
    logger.close()

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["frame_id"] == 1
    assert payload["actuator_command"] is None


def test_runtime_trace_logger_is_noop_when_disabled(tmp_path: Path) -> None:
    logger = RuntimeTraceLogger(None)

    logger.open()
    logger.write(
        RuntimeTraceEntry(
            timestamp=1.0,
            frame_id=99,
            lane_id=-1,
            bbox=(0.0, 0.0, 0.0, 0.0),
            color_class="unknown",
            confidence=0.0,
            decision="accept",
            actuator_command=None,
            latency_ms=0.0,
        )
    )
    logger.close()

    assert list(tmp_path.iterdir()) == []
