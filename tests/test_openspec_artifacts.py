from __future__ import annotations

import json
from pathlib import Path


REQUIRED_ARTIFACTS = (
    "docs/openspec/v3/state_machine.md",
    "docs/openspec/v3/protocol_compliance_matrix.md",
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
