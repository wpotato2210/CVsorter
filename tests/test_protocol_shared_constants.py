from __future__ import annotations

import json
from pathlib import Path

from coloursorter.protocol.constants import (
    ALLOWED_MODES,
    ALLOWED_SCHEDULER_STATES,
    CMD_GET_STATE,
    CMD_RESET_QUEUE,
    CMD_SCHED,
    CMD_SET_MODE,
    LANE_MAX,
    LANE_MIN,
    NACK_ARG_COUNT_MISMATCH,
    NACK_ARG_RANGE_ERROR,
    NACK_ARG_TYPE_ERROR,
    NACK_BUSY,
    NACK_CODE_MAX,
    NACK_CODE_MIN,
    NACK_INVALID_MODE_TRANSITION,
    NACK_MALFORMED_FRAME,
    NACK_QUEUE_FULL,
    NACK_UNKNOWN_COMMAND,
    QUEUE_DEPTH_MIN,
    TRIGGER_MM_MAX,
    TRIGGER_MM_MIN,
)


COMMANDS_PATH = Path("docs/openspec/v3/protocol/commands.json")
MCU_RESPONSE_SCHEMA_PATH = Path("docs/openspec/v3/contracts/mcu_response_schema.json")


def test_protocol_constants_match_commands_json_contract() -> None:
    commands_spec = json.loads(COMMANDS_PATH.read_text(encoding="utf-8"))
    commands_by_name = {command["name"]: command for command in commands_spec["commands"]}

    assert set(commands_by_name) == {CMD_SET_MODE, CMD_SCHED, CMD_GET_STATE, CMD_RESET_QUEUE}

    mode_arg = commands_by_name[CMD_SET_MODE]["args"][0]
    assert set(mode_arg["allowed"]) == ALLOWED_MODES

    sched_args = commands_by_name[CMD_SCHED]["args"]
    lane_arg, trigger_arg = sched_args
    assert lane_arg["min"] == LANE_MIN
    assert lane_arg["max"] == LANE_MAX
    assert trigger_arg["min"] == TRIGGER_MM_MIN
    assert trigger_arg["max"] == TRIGGER_MM_MAX

    expected_nack_codes = {
        str(NACK_UNKNOWN_COMMAND): "UNKNOWN_COMMAND",
        str(NACK_ARG_COUNT_MISMATCH): "ARG_COUNT_MISMATCH",
        str(NACK_ARG_RANGE_ERROR): "ARG_RANGE_ERROR",
        str(NACK_ARG_TYPE_ERROR): "ARG_TYPE_ERROR",
        str(NACK_INVALID_MODE_TRANSITION): "INVALID_MODE_TRANSITION",
        str(NACK_QUEUE_FULL): "QUEUE_FULL",
        str(NACK_BUSY): "BUSY",
        str(NACK_MALFORMED_FRAME): "MALFORMED_FRAME",
    }
    assert commands_spec["ack_nack"]["nack_codes"] == expected_nack_codes


def test_protocol_constants_match_mcu_response_schema_contract() -> None:
    schema = json.loads(MCU_RESPONSE_SCHEMA_PATH.read_text(encoding="utf-8"))
    properties = schema["properties"]

    assert properties["nack_code"]["minimum"] == NACK_CODE_MIN
    assert properties["nack_code"]["maximum"] == NACK_CODE_MAX
    assert properties["queue_depth"]["minimum"] == QUEUE_DEPTH_MIN
    assert set(properties["mode"]["enum"]) == ALLOWED_MODES
    assert set(properties["scheduler_state"]["enum"]) == ALLOWED_SCHEDULER_STATES
