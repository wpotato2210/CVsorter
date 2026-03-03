from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.bench.esp32_transport import Esp32McuTransport
from coloursorter.bench.types import AckCode, FaultState
from coloursorter.protocol import MODE_TRANSITIONS, OpenSpecV3Host, is_mode_transition_allowed
from coloursorter.protocol.nack_codes import CANONICAL_NACK_7, DETAIL_BUSY, NACK_BUSY
from coloursorter.scheduler import ScheduledCommand
from coloursorter.serial_interface import parse_ack_tokens, parse_frame
from coloursorter.bench.serial_transport import SerialTransportConfig


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
    assert _response_tokens(host.handle_frame("<GET_STATE>"))[:2] == ["NACK", str(NACK_BUSY)]
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


def test_nack_code_7_is_canonical_busy_only() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)
    host.busy = True

    ack = parse_ack_tokens(_response_tokens(host.handle_frame("<GET_STATE>")))

    assert ack.status == "NACK"
    assert ack.nack_code == NACK_BUSY
    assert ack.detail == DETAIL_BUSY
    assert (ack.nack_code, ack.detail) == CANONICAL_NACK_7

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


def test_mode_transition_policy_matrix_is_canonical_for_gui_and_host() -> None:
    assert MODE_TRANSITIONS["SAFE"] == frozenset({"SAFE", "MANUAL"})
    assert is_mode_transition_allowed("SAFE", "MANUAL") is True
    assert is_mode_transition_allowed("SAFE", "AUTO") is False
    assert is_mode_transition_allowed("MANUAL", "AUTO") is True


def test_host_enforces_shared_mode_transition_policy() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    parse_ack_tokens(_response_tokens(host.handle_frame("<SET_MODE|SAFE>")))
    safe_to_auto = parse_ack_tokens(_response_tokens(host.handle_frame("<SET_MODE|AUTO>")))
    safe_to_manual = parse_ack_tokens(_response_tokens(host.handle_frame("<SET_MODE|MANUAL>")))
    manual_to_auto = parse_ack_tokens(_response_tokens(host.handle_frame("<SET_MODE|AUTO>")))

    assert safe_to_auto.status == "NACK"
    assert safe_to_auto.nack_code == 5
    assert safe_to_manual.status == "ACK"
    assert manual_to_auto.status == "ACK"


@pytest.mark.parametrize("current_mode", ["AUTO", "MANUAL", "SAFE"])
@pytest.mark.parametrize("target_mode", ["AUTO", "MANUAL", "SAFE"])
def test_set_mode_results_match_policy_helper_for_every_mode_pair(current_mode: str, target_mode: str) -> None:
    host = OpenSpecV3Host(max_queue_depth=2, mode=current_mode)

    result = parse_ack_tokens(_response_tokens(host.handle_frame(f"<SET_MODE|{target_mode}>")))

    expected_allowed = is_mode_transition_allowed(current_mode, target_mode)
    expected_status = "ACK" if expected_allowed else "NACK"
    assert result.status == expected_status


@pytest.mark.parametrize(
    ("current_mode", "target_mode", "expected_status"),
    [
        ("AUTO", "AUTO", "ACK"),
        ("AUTO", "MANUAL", "ACK"),
        ("AUTO", "SAFE", "ACK"),
        ("MANUAL", "AUTO", "ACK"),
        ("MANUAL", "MANUAL", "ACK"),
        ("MANUAL", "SAFE", "ACK"),
        ("SAFE", "AUTO", "NACK"),
        ("SAFE", "MANUAL", "ACK"),
        ("SAFE", "SAFE", "ACK"),
    ],
)
def test_host_mode_transition_outcomes_match_contract(
    current_mode: str, target_mode: str, expected_status: str
) -> None:
    host = OpenSpecV3Host(max_queue_depth=2, mode=current_mode)

    result = parse_ack_tokens(_response_tokens(host.handle_frame(f"<SET_MODE|{target_mode}>")))

    assert result.status == expected_status


class _HostBackedSerial:
    def __init__(self, host: OpenSpecV3Host) -> None:
        self._host = host

    def write(self, _payload: bytes) -> None:
        return None

    def readline(self) -> bytes:
        return self._host.handle_frame("<SCHED|1|100.0>").encode() + b"\n"


def test_esp32_adapter_preserves_protocol_ack_parsing_invariants() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    transport = Esp32McuTransport(
        config=SerialTransportConfig(port="/dev/null", baud=115200, timeout_s=0.05),
        serial_factory=lambda **_: _HostBackedSerial(host),
    )

    response = transport.send(ScheduledCommand(lane=1, position_mm=100.0))

    assert response.ack_code == AckCode.ACK
    assert response.fault_state == FaultState.NORMAL
    assert response.queue_depth == 1
