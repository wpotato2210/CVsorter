#!/usr/bin/env python3
"""Validate firmware readiness contracts, protocol parity, and runtime config presence."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
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




def _load_protocol_authority_module():
    authority_path = Path("src/coloursorter/protocol/authority.py")
    spec = importlib.util.spec_from_file_location("coloursorter_protocol_authority", authority_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load protocol authority module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def check_protocol_constants() -> CheckResult:
    constants = _load_protocol_constants_module()
    authority = _load_protocol_authority_module()
    commands_path = Path(authority.AUTHORITATIVE_PROTOCOL_JSON)
    commands_json = _load_json(commands_path)

    command_names = {entry["name"] for entry in commands_json["commands"]}
    runtime_names = set(constants.SUPPORTED_COMMANDS)
    if command_names != runtime_names:
        return CheckResult(
            name="protocol_constants",
            passed=False,
            detail=f"command mismatch: json={sorted(command_names)} runtime={sorted(runtime_names)}",
        )

    if commands_json["startup"]["protocol_version"] != constants.SUPPORTED_PROTOCOL_VERSION:
        return CheckResult(name="protocol_constants", passed=False, detail="startup.protocol_version mismatch")

    if set(commands_json["startup"]["capabilities"]) != set(constants.SUPPORTED_CAPABILITIES):
        return CheckResult(name="protocol_constants", passed=False, detail="startup.capabilities mismatch")

    if commands_json["ack_nack"]["ack_token"] != constants.ACK_TOKEN:
        return CheckResult(name="protocol_constants", passed=False, detail="ack token mismatch")

    if commands_json["ack_nack"]["nack_token"] != constants.NACK_TOKEN:
        return CheckResult(name="protocol_constants", passed=False, detail="nack token mismatch")

    nack_codes = commands_json["ack_nack"]["nack_codes"]
    if {int(code) for code in nack_codes} != set(range(constants.NACK_CODE_MIN, constants.NACK_CODE_MAX + 1)):
        return CheckResult(name="protocol_constants", passed=False, detail="nack code range mismatch")

    return CheckResult(name="protocol_constants", passed=True, detail=f"constants match {commands_path}")


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

    src_path = Path("src").resolve()
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    runtime_module_path = Path("src/coloursorter/config/runtime.py")
    deploy_module_name = "coloursorter.deploy"
    had_deploy_module = deploy_module_name in sys.modules
    original_deploy_module = sys.modules.get(deploy_module_name)

    def _resolve_detection_provider_name(provider_name: str) -> str:
        normalized = provider_name.strip()
        if not normalized:
            raise ValueError("detection provider name must be a non-empty string")
        allowed_values = ("opencv_basic", "opencv_calibrated", "model_stub")
        if normalized not in allowed_values:
            allowed = ", ".join(allowed_values)
            raise ValueError(f"Unsupported detection provider: {normalized}. Allowed: {allowed}")
        return normalized

    try:
        deploy_stub = types.ModuleType(deploy_module_name)
        deploy_stub.DETECTION_PROVIDER_VALUES = ("opencv_basic", "opencv_calibrated", "model_stub")
        deploy_stub.resolve_detection_provider_name = _resolve_detection_provider_name
        sys.modules[deploy_module_name] = deploy_stub
        runtime_spec = importlib.util.spec_from_file_location("firmware_readiness_runtime", runtime_module_path)
        if runtime_spec is None or runtime_spec.loader is None:
            return CheckResult(name="runtime_config", passed=False, detail="unable to load runtime validator module")
        runtime_module = importlib.util.module_from_spec(runtime_spec)
        sys.modules[runtime_spec.name] = runtime_module
        runtime_spec.loader.exec_module(runtime_module)
    except Exception as exc:  # pragma: no cover - import failure only
        return CheckResult(name="runtime_config", passed=False, detail=f"unable to import runtime config validator: {exc}")
    finally:
        sys.modules.pop("firmware_readiness_runtime", None)
        if had_deploy_module:
            sys.modules[deploy_module_name] = original_deploy_module
        else:
            sys.modules.pop(deploy_module_name, None)

    try:
        runtime_module.RuntimeConfig.load_startup(config_path)
    except runtime_module.ConfigValidationError as exc:
        return CheckResult(name="runtime_config", passed=False, detail=f"invalid runtime config: {exc}")
    except Exception as exc:  # pragma: no cover - unexpected parser/runtime failure
        return CheckResult(name="runtime_config", passed=False, detail=f"runtime config load failure: {exc}")

    return CheckResult(name="runtime_config", passed=True, detail="RuntimeConfig.load_startup validation passed")


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
