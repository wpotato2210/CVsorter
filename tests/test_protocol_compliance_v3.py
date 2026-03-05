from __future__ import annotations

import json
from pathlib import Path

import pytest

from coloursorter.bench.esp32_transport import Esp32McuTransport
from coloursorter.bench.serial_transport import SerialTransportConfig
from coloursorter.bench.types import AckCode, FaultState
from coloursorter.protocol import MODE_TRANSITIONS, OpenSpecV3Host, is_mode_transition_allowed
from coloursorter.protocol.nack_codes import CANONICAL_NACK_7, DETAIL_BUSY, NACK_BUSY
from coloursorter.scheduler import ScheduledCommand
from coloursorter.serial_interface import parse_ack_tokens, parse_frame, serialize_packet


def _response_tokens(frame: str) -> list[str]:
    parsed = parse_frame(frame)
    return [parsed.command, *parsed.args]


def test_commands_contract_lane_max_is_22_lane_system() -> None:
    commands = json.loads(Path("docs/openspec/v3/protocol/commands.json").read_text(encoding="utf-8"))
    sched = next(command for command in commands["commands"] if command["name"] == "SCHED")
    assert sched["args"][0]["max"] == 21


def test_protocol_supports_all_v3_commands_with_handshake() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)

    assert parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1")))).status == "ACK"
    assert parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2")))).status == "ACK"
    assert parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("GET_STATE", (), msg_id="3")))).status == "ACK"
    assert parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("SCHED", (0, "100.0"), msg_id="4")))).status == "ACK"
    assert parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("RESET_QUEUE", (), msg_id="5")))).status == "ACK"
    assert parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("SET_MODE", ("MANUAL",), msg_id="6")))).status == "ACK"


def test_nack_semantics_align_to_spec_codes_1_to_8() -> None:
    host = OpenSpecV3Host(max_queue_depth=1)
    host.busy = True
    busy_ack = parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("GET_STATE", (), msg_id="1"))))
    assert busy_ack.status == "NACK"
    assert (busy_ack.nack_code, busy_ack.detail) == CANONICAL_NACK_7
    host.busy = False

    assert _response_tokens(host.handle_frame(serialize_packet("UNKNOWN", (), msg_id="2")))[:2] == ["NACK", "1"]
    assert _response_tokens(host.handle_frame(serialize_packet("SCHED", (1,), msg_id="3")))[:2] == ["NACK", "5"]


def test_nack_code_7_is_canonical_busy_only() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)
    host.busy = True

    ack = parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("GET_STATE", (), msg_id="1"))))

    assert ack.status == "NACK"
    assert ack.nack_code == NACK_BUSY
    assert ack.detail == DETAIL_BUSY
    assert (ack.nack_code, ack.detail) == CANONICAL_NACK_7


def test_ack_metadata_parsing_mode_queue_scheduler_and_queue_cleared() -> None:
    host = OpenSpecV3Host(max_queue_depth=4)
    host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"))
    host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2"))
    host.handle_frame(serialize_packet("SCHED", (1, "120.0"), msg_id="3"))
    ack = parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("SET_MODE", ("MANUAL",), msg_id="4"))))

    assert ack.mode == "MANUAL"
    assert ack.queue_depth == 0
    assert ack.scheduler_state == "IDLE"
    assert ack.queue_cleared is True
    assert ack.link_state in {"READY", "DEGRADED", "SYNCING", "DISCONNECTED"}




def test_set_mode_rejects_safe_to_auto_with_canonical_nack_5_detail() -> None:
    host = OpenSpecV3Host(max_queue_depth=2, mode="SAFE")
    host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"))
    host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2"))

    ack = parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("SET_MODE", ("AUTO",), msg_id="3"))))

    assert ack.status == "NACK"
    assert ack.nack_code == 5
    assert ack.detail == "INVALID_MODE_TRANSITION"


def test_set_mode_allows_safe_to_manual_then_manual_to_auto_recovery() -> None:
    host = OpenSpecV3Host(max_queue_depth=2, mode="SAFE")
    host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"))
    host.handle_frame(serialize_packet("HEARTBEAT", (), msg_id="2"))

    safe_to_manual = parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("SET_MODE", ("MANUAL",), msg_id="3"))))
    manual_to_auto = parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("SET_MODE", ("AUTO",), msg_id="4"))))

    assert safe_to_manual.status == "ACK"
    assert manual_to_auto.status == "ACK"
    assert host.mode == "AUTO"

def test_mode_transition_policy_matrix_is_canonical_for_gui_and_host() -> None:
    assert MODE_TRANSITIONS["SAFE"] == frozenset({"SAFE", "MANUAL"})
    assert is_mode_transition_allowed("SAFE", "MANUAL") is True
    assert is_mode_transition_allowed("SAFE", "AUTO") is False
    assert is_mode_transition_allowed("MANUAL", "AUTO") is True


class _HostBackedSerial:
    def __init__(self, host: OpenSpecV3Host) -> None:
        self._host = host
        self._last: bytes = b""

    def write(self, payload: bytes) -> None:
        self._last = payload

    def readline(self) -> bytes:
        return self._host.handle_frame(self._last.decode().strip()).encode() + b"\n"


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


def test_sched_before_link_ready_uses_canonical_busy_pair() -> None:
    host = OpenSpecV3Host(max_queue_depth=2)
    host.handle_frame(serialize_packet("HELLO", ("3.1", "CRC32;SCHED;HEARTBEAT;DEDUPE"), msg_id="1"))

    ack = parse_ack_tokens(_response_tokens(host.handle_frame(serialize_packet("SCHED", (0, "10.0"), msg_id="2"))))

    assert ack.status == "NACK"
    assert (ack.nack_code, ack.detail) == CANONICAL_NACK_7
