from __future__ import annotations

import json
from pathlib import Path

from coloursorter.bench import AckCode, BenchLogEntry
from coloursorter.bench.evaluation import write_artifacts
from coloursorter.serial_interface.serial_interface import parse_frame, serialize_packet

FIXTURE_PATH = Path("tests/fixtures/trigger_correlation_t3_003.json")


class _EvaluationStub:
    passed = True
    summary: dict[str, object] = {}
    scenarios: tuple[object, ...] = ()


def _load_vectors() -> tuple[dict[str, object], ...]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        raise AssertionError("fixture vectors must be a non-empty list")
    return tuple(vectors)


def _status_from_event(event: dict[str, object]) -> str:
    if bool(event["scheduler_window_missed"]):
        return "terminal_missed_window"
    if bool(event["transport_acknowledged"]) and bool(event["actuator_command_issued"]):
        return "terminal_acknowledged"
    return "terminal_not_observed"


def _log_entry_from_vector(vector: dict[str, object]) -> BenchLogEntry:
    status = str(vector["terminal_status"])
    lane = int(vector["lane"])
    msg_id = str(vector["msg_id"])
    command = str(vector["command"])
    return BenchLogEntry(
        run_id="r-t3-003-gate",
        test_batch_id="b-t3-003-gate",
        event_timestamp_utc="2024-01-01T00:00:00+00:00",
        frame_timestamp_s=0.0,
        trigger_generation_s=0.0,
        frame_id=1,
        object_id=f"obj-{msg_id}",
        lane=lane,
        lane_index=lane,
        decision="reject",
        decision_reason="phase3_t3_003_gate",
        prediction_label="reject",
        confidence=1.0,
        rejection_reason="classified_reject",
        protocol_round_trip_ms=1.0,
        ack_code=AckCode.ACK,
        protocol_frame=serialize_packet(command, [lane, 120.0], msg_id=msg_id),
        transport_sent=True,
        transport_acknowledged=status != "terminal_not_observed",
        actuator_command_issued=status == "terminal_acknowledged",
        scheduler_window_missed=status == "terminal_missed_window",
    )


def test_t3_003_each_accepted_command_has_terminal_status(tmp_path: Path) -> None:
    vectors = tuple(vector for vector in _load_vectors() if bool(vector["accepted"]))
    logs = tuple(_log_entry_from_vector(vector) for vector in vectors)

    artifact_dir = write_artifacts(
        logs,
        _EvaluationStub(),
        tmp_path / "reconciliation_gate",
        include_text_report=False,
    )
    events = [
        json.loads(line)
        for line in (artifact_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    observed: dict[tuple[str, str, int], str] = {}
    for event in events:
        packet = parse_frame(str(event["protocol_frame"]))
        key = (packet.msg_id, packet.command, int(event["lane_index"]))
        status = _status_from_event(event)
        if key in observed:
            raise AssertionError(f"duplicate terminal status for correlation key: {key}")
        observed[key] = status

    expected = {
        (str(vector["msg_id"]), str(vector["command"]), int(vector["lane"])): str(vector["terminal_status"])
        for vector in vectors
    }
    assert observed == expected
