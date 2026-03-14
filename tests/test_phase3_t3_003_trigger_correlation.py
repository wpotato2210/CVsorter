from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.bench import AckCode, BenchLogEntry
from coloursorter.serial_interface.serial_interface import parse_frame, serialize_packet


FIXTURE_PATH = Path("tests/fixtures/trigger_correlation_t3_003.json")


class CorrelationKey(tuple[str, str, int]):
    """Deterministic key: (msg_id, command, lane_index)."""


TERMINAL_STATUSES = {
    "terminal_acknowledged",
    "terminal_missed_window",
    "terminal_not_observed",
}


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        raise AssertionError("fixture vectors must be a non-empty list")
    return payload


def _status_from_entry(entry: BenchLogEntry) -> str:
    if entry.scheduler_window_missed:
        return "terminal_missed_window"
    if entry.transport_acknowledged and entry.actuator_command_issued:
        return "terminal_acknowledged"
    return "terminal_not_observed"


def _build_entry(*, msg_id: str, command: str, lane: int, terminal_status: str) -> BenchLogEntry:
    if terminal_status not in TERMINAL_STATUSES:
        raise AssertionError(f"unknown terminal_status: {terminal_status}")

    return BenchLogEntry(
        run_id="r-t3-003",
        test_batch_id="b-t3-003",
        event_timestamp_utc="2024-01-01T00:00:00+00:00",
        frame_timestamp_s=0.0,
        trigger_generation_s=0.0,
        frame_id=1,
        object_id=f"obj-{msg_id}",
        lane=lane,
        lane_index=lane,
        decision="reject",
        decision_reason="phase3_t3_003",
        prediction_label="reject",
        confidence=1.0,
        rejection_reason="classified_reject",
        protocol_round_trip_ms=1.0,
        ack_code=AckCode.ACK,
        protocol_frame=serialize_packet(command, [lane, 120.0], msg_id=msg_id),
        transport_sent=True,
        transport_acknowledged=terminal_status != "terminal_not_observed",
        actuator_command_issued=terminal_status == "terminal_acknowledged",
        scheduler_window_missed=terminal_status == "terminal_missed_window",
    )


def _reconcile_terminal_statuses(entries: list[BenchLogEntry]) -> dict[CorrelationKey, str]:
    observed: dict[CorrelationKey, str] = {}
    for entry in entries:
        if entry.ack_code != AckCode.ACK:
            continue
        packet = parse_frame(entry.protocol_frame)
        if packet.command != "SCHED":
            continue
        key = CorrelationKey((packet.msg_id, packet.command, int(entry.lane_index)))
        if key in observed:
            raise AssertionError(f"duplicate terminal status for correlation key: {key}")
        observed[key] = _status_from_entry(entry)
    return observed


def _expected_sched_mapping(payload: dict[str, object]) -> dict[CorrelationKey, str]:
    vectors = payload["vectors"]
    accepted_sched_vectors = [
        vector
        for vector in vectors
        if bool(vector["accepted"]) and str(vector["command"]) == "SCHED"
    ]

    return {
        CorrelationKey((str(vector["msg_id"]), "SCHED", int(vector["lane"]))): str(vector["terminal_status"])
        for vector in accepted_sched_vectors
    }


def test_t3_003_sched_commands_map_to_exactly_one_terminal_status() -> None:
    payload = _load_fixture()
    expected = _expected_sched_mapping(payload)

    entries = [
        _build_entry(
            msg_id=str(vector["msg_id"]),
            command=str(vector["command"]),
            lane=int(vector["lane"]),
            terminal_status=str(vector["terminal_status"]),
        )
        for vector in payload["vectors"]
        if bool(vector["accepted"])
    ]

    observed = _reconcile_terminal_statuses(entries)
    assert observed == expected


def test_t3_003_reconciler_rejects_duplicate_sched_terminal_status() -> None:
    payload = _load_fixture()
    expected = _expected_sched_mapping(payload)
    duplicate_key = next(iter(expected))

    entries = [
        _build_entry(msg_id=key[0], command=key[1], lane=key[2], terminal_status=status)
        for key, status in expected.items()
    ]
    entries.append(
        _build_entry(
            msg_id=duplicate_key[0],
            command=duplicate_key[1],
            lane=duplicate_key[2],
            terminal_status=expected[duplicate_key],
        )
    )

    with pytest.raises(AssertionError, match="duplicate terminal status"):
        _reconcile_terminal_statuses(entries)


def test_t3_003_reconciler_detects_missing_sched_terminal_status() -> None:
    payload = _load_fixture()
    expected = _expected_sched_mapping(payload)

    entries = [
        _build_entry(msg_id=key[0], command=key[1], lane=key[2], terminal_status=status)
        for key, status in expected.items()
    ]
    entries.pop()

    observed = _reconcile_terminal_statuses(entries)
    missing = sorted(set(expected) - set(observed))

    assert missing, "at least one accepted SCHED key must be missing"
