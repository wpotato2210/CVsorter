#!/usr/bin/env python3
"""Validate firmware readiness contracts, protocol parity, and runtime config presence."""

from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_protocol_constants_module():
    constants_path = Path("src/coloursorter/protocol/constants.py")
    spec = importlib.util.spec_from_file_location("coloursorter_protocol_constants", constants_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load protocol constants module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_protocol_constants() -> CheckResult:
    constants = _load_protocol_constants_module()
    commands_json = _load_json(Path("protocol/commands.json"))
    command_names = {entry["name"] for entry in commands_json["commands"]}
    runtime_names = set(constants.SUPPORTED_COMMANDS)
    if command_names != runtime_names:
        return CheckResult(
            name="protocol_constants",
            passed=False,
            detail=f"command mismatch: json={sorted(command_names)} runtime={sorted(runtime_names)}",
        )
    return CheckResult(name="protocol_constants", passed=True, detail="constants match protocol/commands.json")


def check_schema_hardening() -> CheckResult:
    runtime_schema = _load_json(Path("contracts/mcu_response_schema.json"))
    docs_schema = _load_json(Path("docs/openspec/v3/contracts/mcu_response_schema.json"))
    if runtime_schema != docs_schema:
        return CheckResult(name="mcu_response_schema", passed=False, detail="runtime/docs schema mismatch")

    all_of = runtime_schema.get("allOf", [])
    if not all_of:
        return CheckResult(name="mcu_response_schema", passed=False, detail="missing allOf conditional rules")

    status_prop = runtime_schema.get("properties", {}).get("status", {})
    if set(status_prop.get("enum", [])) != {"ACK", "NACK"}:
        return CheckResult(name="mcu_response_schema", passed=False, detail="status enum must be ACK/NACK")

    return CheckResult(name="mcu_response_schema", passed=True, detail="schema parity and conditional structure verified")


def check_runtime_config() -> CheckResult:
    config_path = Path("configs/bench_runtime.yaml")
    if not config_path.exists():
        return CheckResult(name="runtime_config", passed=False, detail="configs/bench_runtime.yaml missing")

    raw = config_path.read_text(encoding="utf-8")
    required_sections = (
        "frame_source:",
        "camera:",
        "transport:",
        "cycle_timing:",
        "cycle_latency_budget:",
        "scheduling_guard:",
        "scenario_thresholds:",
        "detection:",
        "baseline_run:",
        "bench_gui:",
    )
    missing = [section for section in required_sections if section not in raw]
    if missing:
        return CheckResult(name="runtime_config", passed=False, detail=f"missing sections: {', '.join(missing)}")
    return CheckResult(name="runtime_config", passed=True, detail="required runtime sections present")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit non-zero if any check fails")
    args = parser.parse_args()

    checks = (
        check_protocol_constants(),
        check_schema_hardening(),
        check_runtime_config(),
    )

    print("Firmware Readiness Check")
    print("=" * 24)
    all_pass = True
    for result in checks:
        status = "PASS" if result.passed else "FAIL"
        all_pass = all_pass and result.passed
        print(f"- {result.name}: {status} ({result.detail})")
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")

    if args.strict and not all_pass:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
