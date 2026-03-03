from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _matches_const_if_branch(branch: dict[str, Any], payload: dict[str, Any]) -> bool:
    required = branch.get("required", [])
    for key in required:
        if key not in payload:
            return False
    status_const = branch.get("properties", {}).get("status", {}).get("const")
    if status_const is None:
        return True
    return payload.get("status") == status_const


def _validate_mcu_response_fixture(
    schema: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[bool, str | None]:
    properties = schema["properties"]

    for key in schema.get("required", []):
        if key not in payload:
            return False, f"missing required key: {key}"

    if schema.get("additionalProperties") is False:
        extras = [key for key in payload if key not in properties]
        if extras:
            return False, f"unknown properties: {extras}"

    for key, value in payload.items():
        if key not in properties:
            continue
        spec = properties[key]
        expected_type = spec.get("type")
        if expected_type == "string" and not isinstance(value, str):
            return False, f"{key} must be string"
        if expected_type == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            return False, f"{key} must be integer"
        if expected_type == "boolean" and not isinstance(value, bool):
            return False, f"{key} must be boolean"

        enum_values = spec.get("enum")
        if enum_values is not None and value not in enum_values:
            return False, f"{key} must be in enum"

        if isinstance(value, int) and not isinstance(value, bool):
            min_value = spec.get("minimum")
            max_value = spec.get("maximum")
            if min_value is not None and value < min_value:
                return False, f"{key} below minimum"
            if max_value is not None and value > max_value:
                return False, f"{key} above maximum"

    for clause in schema.get("allOf", []):
        if _matches_const_if_branch(clause.get("if", {}), payload):
            for key in clause.get("then", {}).get("required", []):
                if key not in payload:
                    return False, f"missing conditional key: {key}"

    return True, None


REQUIRED_ARTIFACTS = (
    "docs/openspec/icd.md",
    "docs/openspec/v3/state_machine.md",
    "docs/openspec/v3/protocol_compliance_matrix.md",
    "docs/openspec/v3/system_compliance_matrix.md",
    "docs/openspec/v3/timing_budget.md",
    "docs/openspec/v3/telemetry_schema.md",
)


def test_required_openspec_v3_artifacts_are_present() -> None:
    for rel in REQUIRED_ARTIFACTS:
        assert Path(rel).exists(), rel


def test_mcu_response_schema_matches_runtime_scheduler_states() -> None:
    runtime = json.loads(Path("contracts/mcu_response_schema.json").read_text(encoding="utf-8"))
    spec = json.loads(Path("docs/openspec/v3/contracts/mcu_response_schema.json").read_text(encoding="utf-8"))

    runtime_states = runtime["properties"]["scheduler_state"]["enum"]
    spec_states = spec["properties"]["scheduler_state"]["enum"]
    assert runtime_states == ["IDLE", "ACTIVE"]
    assert spec_states == runtime_states


def test_mcu_response_schema_nack_range_matches_v3_protocol() -> None:
    runtime = json.loads(Path("contracts/mcu_response_schema.json").read_text(encoding="utf-8"))
    v3_commands = json.loads(Path("docs/openspec/v3/protocol/commands.json").read_text(encoding="utf-8"))

    nack_codes = v3_commands["ack_nack"]["nack_codes"]
    nack_schema = runtime["properties"]["nack_code"]

    assert nack_schema["minimum"] == 1
    assert nack_schema["maximum"] == len(nack_codes)


def test_mcu_response_schema_enforces_conditional_ack_nack_requirements() -> None:
    runtime = json.loads(Path("contracts/mcu_response_schema.json").read_text(encoding="utf-8"))
    spec = json.loads(Path("docs/openspec/v3/contracts/mcu_response_schema.json").read_text(encoding="utf-8"))

    assert runtime["additionalProperties"] is False
    assert spec["additionalProperties"] is False
    assert spec["allOf"] == runtime["allOf"]

    ack_then = runtime["allOf"][0]["then"]["required"]
    nack_then = runtime["allOf"][1]["then"]["required"]

    assert ack_then == ["mode", "queue_depth", "scheduler_state", "queue_cleared"]
    assert nack_then == ["nack_code"]


def test_icd_cross_references_runtime_and_protocol() -> None:
    icd = Path("docs/openspec/icd.md").read_text(encoding="utf-8")
    assert "docs/openspec/v3/protocol/commands.json" in icd
    assert "src/coloursorter/protocol/host.py" in icd
    assert "src/coloursorter/serial_interface/serial_interface.py" in icd


def test_gui_layout_contract_is_mirrored_in_openspec() -> None:
    runtime = json.loads(Path("gui/ui_main_layout.json").read_text(encoding="utf-8"))
    spec = json.loads(Path("docs/openspec/v3/gui/ui_main_layout.json").read_text(encoding="utf-8"))

    assert spec == runtime

    widget_ids = {widget["id"] for widget in runtime["widgets"]}
    assert {
        "sel_mcu",
        "sel_com_port",
        "sel_baud",
        "ctrl_manual_servo_test",
        "panel_logging",
    }.issubset(widget_ids)


def test_default_config_artifact_is_mirrored_in_openspec() -> None:
    runtime = Path("configs/default_config.yaml").read_text(encoding="utf-8")
    spec = Path("docs/openspec/v3/configs/default_config.yaml").read_text(encoding="utf-8")

    assert spec == runtime

    assert "transport:" in runtime
    assert "kind:" in runtime
    assert "serial:" in runtime
    assert "port:" in runtime
    assert "baud:" in runtime


def test_mcu_response_schema_fixture_examples_cover_positive_and_negative_cases() -> None:
    schema = json.loads(Path("contracts/mcu_response_schema.json").read_text(encoding="utf-8"))

    valid_ack = {
        "msg_id": "12",
        "status": "ACK",
        "mode": "AUTO",
        "queue_depth": 1,
        "scheduler_state": "ACTIVE",
        "queue_cleared": False,
        "link_state": "READY",
    }
    valid_nack = {
        "msg_id": "13",
        "status": "NACK",
        "nack_code": 6,
        "detail": "QUEUE_FULL",
    }
    invalid_ack_missing_queue_depth = {
        "msg_id": "14",
        "status": "ACK",
        "mode": "AUTO",
        "scheduler_state": "IDLE",
        "queue_cleared": False,
    }
    invalid_nack_missing_nack_code = {
        "msg_id": "15",
        "status": "NACK",
        "detail": "ARG_RANGE_ERROR",
    }
    invalid_payload_extra_field = {
        "msg_id": "16",
        "status": "ACK",
        "mode": "MANUAL",
        "queue_depth": 0,
        "scheduler_state": "IDLE",
        "queue_cleared": True,
        "unexpected": "extra",
    }

    assert _validate_mcu_response_fixture(schema, valid_ack)[0] is True
    assert _validate_mcu_response_fixture(schema, valid_nack)[0] is True
    assert _validate_mcu_response_fixture(schema, invalid_ack_missing_queue_depth)[0] is False
    assert _validate_mcu_response_fixture(schema, invalid_nack_missing_nack_code)[0] is False
    assert _validate_mcu_response_fixture(schema, invalid_payload_extra_field)[0] is False
