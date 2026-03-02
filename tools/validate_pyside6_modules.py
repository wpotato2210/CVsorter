#!/usr/bin/env python3
"""Validate runtime-importable PySide6 modules from a YAML spec."""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = PROJECT_ROOT / "docs/openspec/v3/gui/pyside6_runtime_modules.yaml"
INVALID_SEPARATORS = ("/", "\\")


def _parse_required_modules_from_yaml_text(yaml_text: str) -> list[str]:
    """Parse `required_modules` from simple YAML list syntax without external deps."""
    lines = yaml_text.splitlines()

    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped.startswith("required_modules:"):
            base_indent = len(raw_line) - len(raw_line.lstrip(" "))
            modules: list[str] = []

            for child_line in lines[index + 1 :]:
                if not child_line.strip() or child_line.lstrip().startswith("#"):
                    continue

                child_indent = len(child_line) - len(child_line.lstrip(" "))
                if child_indent <= base_indent:
                    break

                child_stripped = child_line.strip()
                if not child_stripped.startswith("- "):
                    continue

                module_name = child_stripped[2:].strip().strip('"').strip("'")
                if not module_name:
                    raise ValueError("All entries in 'required_modules' must be non-empty strings")
                modules.append(module_name)

            if not modules:
                raise ValueError("Expected key 'required_modules' to contain at least one list item")
            return modules

    raise ValueError("Expected key 'required_modules' in YAML spec")


def _load_required_modules(spec_path: Path) -> list[str]:
    if not spec_path.exists():
        raise FileNotFoundError(f"YAML spec not found: {spec_path}")

    modules = _parse_required_modules_from_yaml_text(spec_path.read_text(encoding="utf-8"))
    return [module.strip() for module in modules]


def _module_status(required_modules: list[str]) -> tuple[list[tuple[str, bool]], list[str]]:
    report_rows: list[tuple[str, bool]] = []
    missing: list[str] = []

    for module_name in required_modules:
        spec_found = importlib.util.find_spec(module_name) is not None
        report_rows.append((module_name, spec_found))
        if not spec_found:
            missing.append(module_name)

    return report_rows, missing


def _pyside6_version() -> str:
    try:
        return importlib_metadata.version("PySide6")
    except importlib_metadata.PackageNotFoundError:
        return "not-installed"


def _print_summary(report_rows: list[tuple[str, bool]], pyside6_version: str) -> None:
    print("PySide6 runtime module validation summary")
    print(f"PySide6 version: {pyside6_version}")
    print("-" * 72)
    print(f"{'Module':55} {'Spec found'}")
    print("-" * 72)
    for module_name, spec_found in report_rows:
        status = "yes" if spec_found else "no"
        print(f"{module_name:55} {status}")
    print("-" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    args = parser.parse_args()

    try:
        required_modules = _load_required_modules(args.spec)
    except Exception as exc:
        print(f"[ERROR] Failed to load required modules from YAML: {exc}")
        return 2

    for module_name in required_modules:
        if any(separator in module_name for separator in INVALID_SEPARATORS):
            print(
                "[ERROR] Invalid module name in YAML: "
                f"'{module_name}'. Use dotted Python import paths, "
                "for example: PySide6.QtStateMachine"
            )
            return 3

    report_rows, missing_modules = _module_status(required_modules)
    pyside6_version = _pyside6_version()
    _print_summary(report_rows, pyside6_version)

    if missing_modules:
        print("[FAIL] One or more required PySide6 runtime modules are missing.")
        print("Missing modules:")
        for module_name in missing_modules:
            print(f"  - {module_name}")
        print(
            "Recommendation: update Python dependencies/environment or "
            "adjust the YAML 'required_modules' list if the requirement changed."
        )
        return 4

    print("[PASS] All required PySide6 runtime modules are importable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
