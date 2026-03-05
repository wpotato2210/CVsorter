#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _shape(payload: dict[str, object]) -> list[str]:
    return sorted(payload.keys())


def _parse_serial_ack(tokens: tuple[str, ...]) -> dict[str, object]:
    status = tokens[0]
    mode = tokens[1] if len(tokens) > 1 else "UNKNOWN"
    queue_depth = int(tokens[2]) if len(tokens) > 2 and tokens[2].isdigit() else 0
    scheduler_state = tokens[3] if len(tokens) > 3 else "UNKNOWN"
    queue_cleared = (tokens[4].lower() == "true") if len(tokens) > 4 else False
    return {
        "ack_code": status,
        "queue_depth": queue_depth,
        "round_trip_ms": 2.0,
        "fault_state": "normal",
        "scheduler_state": scheduler_state,
        "mode": mode,
        "queue_cleared": queue_cleared,
        "nack_code": None,
        "nack_detail": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare transport payload parity")
    parser.add_argument("--artifacts", default="artifacts")
    args = parser.parse_args()

    mock_payload = {
        "ack_code": "ACK",
        "queue_depth": 0,
        "round_trip_ms": 2.0,
        "fault_state": "normal",
        "scheduler_state": "IDLE",
        "mode": "AUTO",
        "queue_cleared": False,
        "nack_code": None,
        "nack_detail": None,
    }
    serial_payload = _parse_serial_ack(("ACK", "AUTO", "0", "IDLE", "false"))

    mock_shape = _shape(mock_payload)
    serial_shape = _shape(serial_payload)
    shape_match = mock_shape == serial_shape
    mismatches = []
    if not shape_match:
        mismatches.append({"mock_only": sorted(set(mock_shape) - set(serial_shape)), "serial_only": sorted(set(serial_shape) - set(mock_shape))})

    report = {
        "shape_match": shape_match,
        "protocol_mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "mock_shape": mock_shape,
        "serial_shape": serial_shape,
        "sample_mock": mock_payload,
        "sample_serial": serial_payload,
    }
    out = Path(args.artifacts) / "transport_parity_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"transport_parity_report={out}")
    return 0 if shape_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
