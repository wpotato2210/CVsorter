#!/usr/bin/env python3
"""Validate required PySide6 submodules for bench GUI runtime."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path


DEFAULT_SPEC_PATH = Path("docs/openspec/v3/gui/pyside6_runtime_modules.yaml")

try:
    import yaml
except Exception:  # noqa: BLE001
    yaml = None


def _load_spec(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse dependency spec; install project dependencies first")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("spec root must be a mapping")
    return data


def _resolve_required_modules(spec: dict) -> tuple[list[str], dict[str, list[str]]]:
    dependencies = spec.get("runtime_dependencies", {})
    if not isinstance(dependencies, dict):
        raise ValueError("runtime_dependencies must be a mapping")

    required = dependencies.get("required_modules", [])
    if not isinstance(required, list):
        raise ValueError("required_modules must be a list")

    components = spec.get("components", {})
    if not isinstance(components, dict):
        raise ValueError("components must be a mapping")

    component_map: dict[str, list[str]] = {}
    for name, body in components.items():
        if not isinstance(body, dict):
            raise ValueError(f"component '{name}' must be a mapping")
        modules = body.get("required_modules", [])
        if not isinstance(modules, list):
            raise ValueError(f"component '{name}' required_modules must be a list")
        component_map[name] = modules

    merged = sorted({*required, *(m for mods in component_map.values() for m in mods)})
    return merged, component_map


def _check_import(module_name: str) -> tuple[bool, str | None]:
    try:
        importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - this is an environment probe
        return False, f"{type(exc).__name__}: {exc}"
    return True, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        type=Path,
        default=DEFAULT_SPEC_PATH,
        help="Path to runtime dependency YAML spec.",
    )
    args = parser.parse_args()

    if not args.spec.exists():
        print(f"[FAIL] Missing spec file: {args.spec}")
        return 2

    try:
        import pyside6  # type: ignore  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] PySide6 distribution not importable: {type(exc).__name__}: {exc}")
        return 3

    from PySide6 import __version__ as pyside6_version

    try:
        spec = _load_spec(args.spec)
        modules, component_map = _resolve_required_modules(spec)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Could not parse spec: {type(exc).__name__}: {exc}")
        return 2

    print(f"PySide6 version: {pyside6_version}")
    print(f"Validation spec: {args.spec}")
    print(f"Modules to validate ({len(modules)}): {', '.join(modules)}")

    missing: list[tuple[str, str]] = []
    for module_name in modules:
        ok, error = _check_import(module_name)
        if ok:
            print(f"[OK] {module_name}")
        else:
            missing.append((module_name, error or "unknown error"))
            print(f"[MISSING] {module_name} -> {error}")

    print("\nComponent dependency summary:")
    for component, required_modules in sorted(component_map.items()):
        print(f"  - {component}: {', '.join(required_modules) if required_modules else '(none)'}")

    if missing:
        print("\n[FAIL] Missing required PySide6 modules detected.")
        return 1

    print("\n[PASS] All required PySide6 modules are importable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
