from __future__ import annotations

import json
from pathlib import Path

from coloursorter.bench import AckCode, BenchLogEntry
from coloursorter.serial_interface.serial_interface import parse_frame, serialize_packet


FIXTURE_PATH = Path("tests/fixtures/trigger_correlation_t3_003.json")


class CorrelationKey(tuple[str, str, int]):
    pass


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return payload


def _status_from_event(event: BenchLogEntry) -> str:
    if event.scheduler_window_missed:
        return "terminal_missed_window"
    if event.transport_acknowledged and event.actuator_command_issued:
        return "terminal_acknowledged"
    return "terminal_not_observed"


def _reconcile_terminal_statuses(events: list[BenchLogEntry]) -> dict[CorrelationKey, str]:
    observed: dict[CorrelationKey, str] = {}
    for event in events:
        if event.ack_code != AckCode.ACK:
            continue
        packet = parse_frame(event.protocol_frame)
        key = CorrelationKey((packet.msg_id, packet.command, int(event.lane_index)))
        if key in observed:
            raise AssertionError(f"duplicate terminal status for correlation key: {key}")
        observed[key] = _status_from_event(event)
    return observed


def test_t3_003_fixture_is_deterministic_and_ordered() -> None:
    payload = _load_fixture()

    assert payload["vector_pack"] == "T3-003"
    assert payload["seed"] == 3003
    assert payload["status_classes"] == [
        "terminal_acknowledged",
        "terminal_missed_window",
        "terminal_not_observed",
    ]

    vectors = payload["vectors"]
    vector_ids = [vector["id"] for vector in vectors]
    assert vector_ids == [
        "accepted_terminal_acknowledged",
        "accepted_terminal_missed_window",
        "accepted_terminal_not_observed",
    ]


def test_t3_003_correlation_key_is_unique_per_vector() -> None:
    payload = _load_fixture()
    vectors = payload["vectors"]

    keys = [
        (str(vector["msg_id"]), str(vector["command"]), int(vector["lane"]))
        for vector in vectors
    ]
    assert len(keys) == len(set(keys))


def _entry_from_vector(vector: dict[str, object]) -> BenchLogEntry:
    status = str(vector["terminal_status"])
    lane = int(vector["lane"])
    command = str(vector["command"])
    msg_id = str(vector["msg_id"])
    return BenchLogEntry(
        run_id="r-t3-003-design",
        test_batch_id="b-t3-003-design",
        event_timestamp_utc="2024-01-01T00:00:00+00:00",
        frame_timestamp_s=0.0,
        trigger_generation_s=0.0,
        frame_id=1,
        object_id=f"obj-{msg_id}",
        lane=lane,
        lane_index=lane,
        decision="reject",
        decision_reason="phase3_t3_003_design",
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


def test_t3_003_runtime_reconciler_matches_expected_terminal_mapping() -> None:
    payload = _load_fixture()
    accepted_vectors = [vector for vector in payload["vectors"] if bool(vector["accepted"])]

    reconciled = _reconcile_terminal_statuses([_entry_from_vector(vector) for vector in accepted_vectors])

    expected = {
        CorrelationKey((str(vector["msg_id"]), str(vector["command"]), int(vector["lane"]))): str(vector["terminal_status"])
        for vector in accepted_vectors
    }

    assert reconciled == expected


def test_t3_003_runtime_reconciler_emits_deterministic_key_type() -> None:
    payload = _load_fixture()
    accepted_vectors = [vector for vector in payload["vectors"] if bool(vector["accepted"])]
    reconciled = _reconcile_terminal_statuses([_entry_from_vector(vector) for vector in accepted_vectors])
    assert all(isinstance(key, CorrelationKey) for key in reconciled)
