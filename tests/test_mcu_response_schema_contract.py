from __future__ import annotations

import json
from pathlib import Path


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
