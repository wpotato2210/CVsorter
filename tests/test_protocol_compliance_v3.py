from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.protocol import OpenSpecV3Host
from coloursorter.serial_interface import parse_ack_tokens, parse_frame


def _response_tokens(frame: str) -> list[str]:
    parsed = parse_frame(frame)
    return [parsed.command, *parsed.args]


def test_commands_contract_lane_max_is_22_lane_system() -> None:
    commands = json.loads(Path("docs/openspec/v3/protocol/commands.json").read_text(encoding="utf-8"))
    sched = next(command for command in commands["commands"] if command["name"] == "SCHED")
    assert sched["args"][0]["max"] == 21


def test_protocol_supports_all_v3_commands() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    assert parse_ack_tokens(_response_tokens(host.handle_frame("<GET_STATE>"))).status == "ACK"
    assert parse_ack_tokens(_response_tokens(host.handle_frame("<SCHED|0|100.0>"))).status == "ACK"
    assert parse_ack_tokens(_response_tokens(host.handle_frame("<RESET_QUEUE>"))).status == "ACK"
    assert parse_ack_tokens(_response_tokens(host.handle_frame("<SET_MODE|MANUAL>"))).status == "ACK"


def test_nack_semantics_align_to_spec_codes_1_to_8() -> None:
    host = OpenSpecV3Host(max_queue_depth=1)
    host.busy = True
    assert _response_tokens(host.handle_frame("<GET_STATE>"))[:2] == ["NACK", "7"]
    host.busy = False

    assert _response_tokens(host.handle_frame("<UNKNOWN>"))[:2] == ["NACK", "1"]
    assert _response_tokens(host.handle_frame("<SCHED|1>"))[:2] == ["NACK", "2"]
    assert _response_tokens(host.handle_frame("<SCHED|22|10.0>"))[:2] == ["NACK", "3"]
    assert _response_tokens(host.handle_frame("<SCHED|LANE|10.0>"))[:2] == ["NACK", "4"]

    host.mode = "SAFE"
    assert _response_tokens(host.handle_frame("<SET_MODE|AUTO>"))[:2] == ["NACK", "5"]
    host.mode = "AUTO"

    assert _response_tokens(host.handle_frame("<SCHED|0|10.0>"))[:1] == ["ACK"]
    assert _response_tokens(host.handle_frame("<SCHED|1|10.0>"))[:2] == ["NACK", "6"]
    assert _response_tokens(host.handle_frame("SCHED|1|10.0"))[:2] == ["NACK", "8"]


def test_ack_metadata_parsing_mode_queue_scheduler_and_queue_cleared() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    host.handle_frame("<SCHED|1|120.0>")
    ack = parse_ack_tokens(_response_tokens(host.handle_frame("<SET_MODE|MANUAL>")))

    assert ack.mode == "MANUAL"
    assert ack.queue_depth == 0
    assert ack.scheduler_state == "IDLE"
    assert ack.queue_cleared is True


def test_set_mode_transition_auto_clears_queue_and_safe_explicit_transition() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    host.handle_frame("<SCHED|1|120.0>")
    host.handle_frame("<SCHED|2|130.0>")

    ack = parse_ack_tokens(_response_tokens(host.handle_frame("<SET_MODE|SAFE>")))
    assert ack.queue_cleared is True
    assert ack.mode == "SAFE"

    back_to_manual = parse_ack_tokens(_response_tokens(host.handle_frame("<SET_MODE|MANUAL>")))
    assert back_to_manual.status == "ACK"


def test_compliance_matrix_artifact_is_present() -> None:
    matrix_path = Path("docs/openspec/v3/protocol_compliance_matrix.md")
    assert matrix_path.exists()
    content = matrix_path.read_text(encoding="utf-8")
    assert "OpenSpec v3 Protocol Compliance Matrix" in content
    assert "NACK-8 MALFORMED_FRAME" in content


def test_scheduler_and_host_trigger_bounds_match() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    assert _response_tokens(host.handle_frame("<SCHED|2|0.0>"))[:1] == ["ACK"]
    assert _response_tokens(host.handle_frame("<SCHED|2|2000.0>"))[:1] == ["ACK"]
    assert _response_tokens(host.handle_frame("<SCHED|2|2000.001>"))[:2] == ["NACK", "3"]
