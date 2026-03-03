from __future__ import annotations

import json
from pathlib import Path


def test_strict_mcu_response_schema_is_mirrored_in_openspec() -> None:
    runtime = json.loads(Path("contracts/mcu_response_schema_strict.json").read_text(encoding="utf-8"))
    spec = json.loads(Path("docs/openspec/v3/contracts/mcu_response_schema_strict.json").read_text(encoding="utf-8"))

    assert spec == runtime
    assert runtime["additionalProperties"] is False


def test_strict_mcu_response_schema_enforces_conditional_ack_nack_requirements() -> None:
    schema = json.loads(Path("contracts/mcu_response_schema_strict.json").read_text(encoding="utf-8"))

    ack_then = schema["allOf"][0]["then"]
    nack_then = schema["allOf"][1]["then"]

    assert ack_then["required"] == ["mode", "queue_depth", "scheduler_state", "queue_cleared"]
    assert ack_then["not"] == {"required": ["nack_code"]}
    assert nack_then["required"] == ["nack_code"]
    assert nack_then["not"] == {
        "anyOf": [
            {"required": ["mode"]},
            {"required": ["queue_depth"]},
            {"required": ["scheduler_state"]},
            {"required": ["queue_cleared"]},
        ]
    }
