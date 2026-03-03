from __future__ import annotations

import json
from pathlib import Path


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
