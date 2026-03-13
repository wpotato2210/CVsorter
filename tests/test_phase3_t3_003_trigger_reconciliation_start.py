from __future__ import annotations

import json
from pathlib import Path

from coloursorter.bench import AckCode, BenchLogEntry
from coloursorter.bench.evaluation import write_artifacts
from coloursorter.serial_interface.serial_interface import parse_frame, serialize_packet

FIXTURE_PATH = Path("tests/fixtures/trigger_correlation_t3_003.json")


def _entry(
    *,
    msg_id: str,
    command: str,
    lane: int,
    actuator_command_issued: bool,
    transport_acknowledged: bool,
    scheduler_window_missed: bool,
) -> BenchLogEntry:
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
        transport_acknowledged=transport_acknowledged,
        actuator_command_issued=actuator_command_issued,
        scheduler_window_missed=scheduler_window_missed,
    )


def _status_from_event(event: dict[str, object]) -> str:
    if bool(event["scheduler_window_missed"]):
        return "terminal_missed_window"
    if bool(event["transport_acknowledged"]) and bool(event["actuator_command_issued"]):
        return "terminal_acknowledged"
    return "terminal_not_observed"


def _load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors = payload.get("vectors")
    if not isinstance(vectors, list):
        raise AssertionError("fixture vectors must be a list")
    return payload


def test_t3_003_runtime_start_reconciles_terminal_statuses(tmp_path: Path) -> None:
    logs = (
        _entry(
            msg_id="m-3003-001",
            command="SCHED",
            lane=0,
            actuator_command_issued=True,
            transport_acknowledged=True,
            scheduler_window_missed=False,
        ),
        _entry(
            msg_id="m-3003-002",
            command="SCHED",
            lane=1,
            actuator_command_issued=False,
            transport_acknowledged=True,
            scheduler_window_missed=True,
        ),
        _entry(
            msg_id="m-3003-003",
            command="SET_MODE",
            lane=0,
            actuator_command_issued=False,
            transport_acknowledged=False,
            scheduler_window_missed=False,
        ),
    )

    evaluation = type("Eval", (), {"passed": True, "summary": {}, "scenarios": ()})()
    artifact_dir = write_artifacts(logs, evaluation, tmp_path / "run_a", include_text_report=False)

    events = [
        json.loads(line)
        for line in (artifact_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    observed = {}
    for event in events:
        packet = parse_frame(str(event["protocol_frame"]))
        key = (packet.msg_id, packet.command, int(event["lane_index"]))
        observed[key] = _status_from_event(event)

    fixture = _load_fixture()
    expected = {
        (str(vector["msg_id"]), str(vector["command"]), int(vector["lane"])): str(vector["terminal_status"])
        for vector in fixture["vectors"]
    }
    assert observed == expected


def test_t3_003_runtime_start_reconciliation_is_deterministic(tmp_path: Path) -> None:
    fixture = _load_fixture()

    def _run_once(run_name: str) -> list[tuple[str, str, int, str]]:
        logs = tuple(
            _entry(
                msg_id=str(vector["msg_id"]),
                command=str(vector["command"]),
                lane=int(vector["lane"]),
                actuator_command_issued=str(vector["terminal_status"]) == "terminal_acknowledged",
                transport_acknowledged=str(vector["terminal_status"]) != "terminal_not_observed",
                scheduler_window_missed=str(vector["terminal_status"]) == "terminal_missed_window",
            )
            for vector in fixture["vectors"]
        )
        evaluation = type("Eval", (), {"passed": True, "summary": {}, "scenarios": ()})()
        artifact_dir = write_artifacts(logs, evaluation, tmp_path / run_name, include_text_report=False)
        events = [
            json.loads(line)
            for line in (artifact_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        reconciled: list[tuple[str, str, int, str]] = []
        for event in events:
            packet = parse_frame(str(event["protocol_frame"]))
            reconciled.append(
                (packet.msg_id, packet.command, int(event["lane_index"]), _status_from_event(event))
            )
        return reconciled

    assert _run_once("run_b") == _run_once("run_c")
