#!/usr/bin/env python3
"""Validate PySide6 runtime module availability for CI."""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import importlib.util
import platform
import re
import struct
import sys
from pathlib import Path
from typing import Any

DEFAULT_SPEC_PATH = Path("docs/openspec/v3/gui/pyside6_runtime_modules.yaml")
DOTTED_MODULE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$")


class ValidationError(Exception):
    """Raised when the runtime spec is invalid."""


def _simple_yaml_runtime_parse(raw: str) -> dict[str, Any]:
    required_modules: list[str] = []
    optional_modules: list[str] = []
    in_runtime = False
    runtime_indent = 0
    current_key: str | None = None
    current_key_indent = 0

    for line in raw.splitlines():
        without_comment = line.split("#", 1)[0].rstrip()
        if not without_comment.strip():
            continue

        indent = len(without_comment) - len(without_comment.lstrip(" "))
        normalized = without_comment.strip()

        if normalized == "runtime:":
            in_runtime = True
            runtime_indent = indent
            current_key = None
            continue

        if in_runtime and indent <= runtime_indent:
            in_runtime = False
            current_key = None

        if not in_runtime:
            continue

        if normalized == "required_modules:":
            current_key = "required_modules"
            current_key_indent = indent
            continue
        if normalized == "optional_modules:":
            current_key = "optional_modules"
            current_key_indent = indent
            continue

        if current_key and indent <= current_key_indent:
            current_key = None

        if current_key and normalized.startswith("- "):
            value = normalized[2:].strip().strip("\"'")
            if current_key == "required_modules":
                required_modules.append(value)
            else:
                optional_modules.append(value)

    return {"runtime": {"required_modules": required_modules, "optional_modules": optional_modules}}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"Spec file not found: {path}")

    raw = path.read_text(encoding="utf-8")
    try:
        import yaml
    except Exception:  # pragma: no cover
        payload = _simple_yaml_runtime_parse(raw)
    else:
        payload = yaml.safe_load(raw)

    if not isinstance(payload, dict):
        raise ValidationError("YAML root must be a mapping/object.")
    return payload


def _ensure_python_architecture() -> list[str]:
    errors: list[str] = []
    if sys.version_info < (3, 9):
        errors.append(f"Python 3.9+ is required; detected {sys.version.split()[0]}.")
    if struct.calcsize("P") * 8 < 64:
        errors.append("64-bit Python runtime is required for CI and PySide6 compatibility.")
    return errors


def _check_pyside6_distribution_alignment(verbose: bool) -> list[str]:
    errors: list[str] = []
    version_map: dict[str, str] = {}

    for dist_name in ("PySide6", "PySide6-Addons"):
        try:
            version_map[dist_name] = importlib_metadata.version(dist_name)
        except importlib_metadata.PackageNotFoundError:
            errors.append(f"Required distribution `{dist_name}` is not installed.")

    if "PySide6" in version_map and "PySide6-Addons" in version_map:
        if version_map["PySide6"] != version_map["PySide6-Addons"]:
            errors.append(
                "PySide6 and PySide6-Addons versions must match exactly; "
                f"found PySide6={version_map['PySide6']} and "
                f"PySide6-Addons={version_map['PySide6-Addons']}."
            )

    if verbose and version_map:
        print(
            f"[INFO] Runtime: python={platform.python_version()} arch={platform.machine()} bits={struct.calcsize('P') * 8}"
        )
        print(
            "[INFO] Distributions: "
            + ", ".join(f"{name}={version}" for name, version in sorted(version_map.items()))
        )

    return errors


def _extract_modules(spec: dict[str, Any]) -> tuple[list[str], list[str]]:
    runtime = spec.get("runtime")
    if not isinstance(runtime, dict):
        raise ValidationError("Spec must include `runtime` mapping.")

    required_modules = runtime.get("required_modules", [])
    optional_modules = runtime.get("optional_modules", [])

    if not isinstance(required_modules, list) or not all(isinstance(item, str) for item in required_modules):
        raise ValidationError("`runtime.required_modules` must be a list of strings.")
    if not isinstance(optional_modules, list) or not all(isinstance(item, str) for item in optional_modules):
        raise ValidationError("`runtime.optional_modules` must be a list of strings.")

    return required_modules, optional_modules


def _validate_module_name(module_name: str) -> str | None:
    if "/" in module_name or "\\" in module_name:
        return (
            "Invalid module path syntax. Use Python dotted imports (example: `PySide6.QtWidgets`) "
            f"and remove filesystem separators: `{module_name}`"
        )
    if not DOTTED_MODULE_PATTERN.match(module_name):
        return (
            "Invalid module name format. Expected dotted import path (example: `PySide6.QtCore`): "
            f"`{module_name}`"
        )
    return None


def _check_module(module_name: str, verbose: bool) -> tuple[bool, str]:
    invalid_reason = _validate_module_name(module_name)
    if invalid_reason:
        print(f"[CHECK][MOD] {module_name} -> invalid")
        if verbose:
            print(f"[INFO][MOD] {invalid_reason}")
        return False, invalid_reason

    spec = importlib.util.find_spec(module_name)
    if spec is None:
        print(f"[CHECK][MOD] {module_name} -> missing")
        return False, f"Runtime module not importable: {module_name}"

    print(f"[CHECK][MOD] {module_name} -> spec_found")
    if verbose:
        print(
            f"[INFO][MOD] {module_name}: origin={spec.origin} loader={type(spec.loader).__name__ if spec.loader else 'None'}"
        )
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH, help="Path to runtime YAML spec")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    failures: list[str] = []
    failures.extend(_ensure_python_architecture())
    failures.extend(_check_pyside6_distribution_alignment(verbose=args.verbose))

    try:
        spec = _load_yaml(args.spec)
        required_modules, optional_modules = _extract_modules(spec)
    except ValidationError as exc:
        print(f"[FAIL][SPEC] {exc}")
        return 2

    for module_name in required_modules:
        ok, reason = _check_module(module_name, verbose=args.verbose)
        if not ok:
            failures.append(reason)

    for module_name in optional_modules:
        invalid_reason = _validate_module_name(module_name)
        if invalid_reason:
            print(f"[CHECK][MOD] {module_name} -> invalid")
            if args.verbose:
                print(f"[INFO][MOD] {invalid_reason}")
            failures.append(invalid_reason)
            continue
        spec_obj = importlib.util.find_spec(module_name)
        if spec_obj is None:
            print(f"[CHECK][MOD] {module_name} -> missing (optional)")
        else:
            print(f"[CHECK][MOD] {module_name} -> spec_found (optional)")
            if args.verbose:
                print(
                    f"[INFO][MOD] {module_name}: origin={spec_obj.origin} loader={type(spec_obj.loader).__name__ if spec_obj.loader else 'None'}"
                )

    if failures:
        print("\n[FAIL] PySide6 runtime module validation failed.")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("\n[PASS] PySide6 runtime module validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
