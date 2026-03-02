#!/usr/bin/env python3
"""Validate runtime dependencies and importable modules from project metadata."""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import importlib.util
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
DEFAULT_REQUIREMENTS_PATH = PROJECT_ROOT / "requirements.txt"
DEFAULT_SPEC_PATH = PROJECT_ROOT / "docs/openspec/v3/gui/pyside6_runtime_modules.yaml"

DIST_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+")


def _normalize_dist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _extract_distribution_name(requirement_line: str) -> str | None:
    candidate = requirement_line.strip()
    if not candidate or candidate.startswith("#"):
        return None
    candidate = candidate.split(";", 1)[0].strip()
    match = DIST_NAME_PATTERN.match(candidate)
    if not match:
        return None
    raw_name = match.group(0)
    return raw_name.split("[", 1)[0]


def _load_required_distributions(pyproject_path: Path, requirements_path: Path) -> list[str]:
    if pyproject_path.exists():
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        dependencies = data.get("project", {}).get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError("project.dependencies must be a list in pyproject.toml")
        required = [_extract_distribution_name(item) for item in dependencies]
    elif requirements_path.exists():
        required = [_extract_distribution_name(line) for line in requirements_path.read_text(encoding="utf-8").splitlines()]
    else:
        raise FileNotFoundError(
            "No dependency metadata found. Expected pyproject.toml or requirements.txt"
        )

    resolved = sorted({_normalize_dist_name(name) for name in required if name})
    if not resolved:
        raise ValueError("No runtime dependencies discovered from project metadata")
    return resolved


def _distribution_module_candidates(distribution_name: str) -> list[str]:
    try:
        distribution = importlib_metadata.distribution(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return []

    modules: list[str] = []
    top_level = distribution.read_text("top_level.txt") or ""
    for line in top_level.splitlines():
        module = line.strip()
        if module and not module.startswith("_"):
            modules.append(module)

    if not modules:
        modules.append(distribution_name.replace("-", "_"))
    return sorted(set(modules))


def _load_pyside6_submodules(spec_path: Path) -> list[str]:
    if not spec_path.exists():
        return []

    try:
        import yaml
    except Exception:
        return []

    payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []

    runtime = payload.get("runtime_dependencies", {})
    if not isinstance(runtime, dict):
        return []

    required_modules = runtime.get("required_modules", [])
    if not isinstance(required_modules, list):
        return []

    return sorted({str(module) for module in required_modules if isinstance(module, str)})


def _check_distributions(distribution_names: list[str], verbose: bool = False) -> tuple[list[str], list[str]]:
    installed: list[str] = []
    missing: list[str] = []
    for dist_name in distribution_names:
        try:
            dist = importlib_metadata.distribution(dist_name)
            installed.append(dist.metadata.get("Name", dist_name))
            if verbose:
                print(f"[PASS][DIST] {dist_name} (installed={dist.version})")
        except importlib_metadata.PackageNotFoundError:
            missing.append(dist_name)
            if verbose:
                print(
                    f"[FAIL][DIST] {dist_name} is not installed. "
                    f"Install project dependencies first: pip install -e ."
                )
    return installed, missing


def _check_modules(module_names: list[str], verbose: bool = False) -> list[str]:
    missing: list[str] = []
    for module_name in sorted(set(module_names)):
        module_spec = importlib.util.find_spec(module_name)
        if verbose:
            print(f"[CHECK][MOD] validating {module_name}")
            print(f"[CHECK][MOD] find_spec({module_name!r}) -> {module_spec!r}")
        if module_spec is None:
            missing.append(module_name)
            if verbose:
                print(f"[FAIL][MOD] {module_name} import spec not found")
        elif verbose:
            print(f"[PASS][MOD] {module_name}")
    return missing


def _detect_pyside6_version() -> str:
    try:
        return importlib_metadata.distribution("pyside6").version
    except importlib_metadata.PackageNotFoundError:
        return "not installed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", type=Path, default=DEFAULT_PYPROJECT_PATH)
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS_PATH)
    parser.add_argument("--pyside6-spec", "--spec", dest="pyside6_spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        required_distributions = _load_required_distributions(args.pyproject, args.requirements)
    except Exception as exc:
        print(f"[FAIL] Could not resolve required distributions: {type(exc).__name__}: {exc}")
        return 2

    if args.verbose:
        print(f"Discovered runtime distributions ({len(required_distributions)}): {', '.join(required_distributions)}")

    _, missing_distributions = _check_distributions(required_distributions, verbose=args.verbose)
    if missing_distributions:
        print("\n[FAIL] Missing required distributions detected.")
        print(f"Missing: {', '.join(missing_distributions)}")
        return 3

    module_candidates: list[str] = []
    for distribution_name in required_distributions:
        module_candidates.extend(_distribution_module_candidates(distribution_name))

    pyside6_related = {d for d in required_distributions if d.startswith("pyside6")}
    if pyside6_related:
        module_candidates.extend(_load_pyside6_submodules(args.pyside6_spec))

    unique_module_candidates = sorted(set(module_candidates))
    if args.verbose:
        print(f"Detected PySide6 version: {_detect_pyside6_version()}")
        print(f"Module checks ({len(unique_module_candidates)}): {', '.join(unique_module_candidates)}")

    missing_modules = _check_modules(unique_module_candidates, verbose=args.verbose)
    if missing_modules:
        print("\n[FAIL] Installed distributions have missing runtime modules.")
        print("Install or repair environment: pip install -e . --force-reinstall")
        print(f"Missing modules: {', '.join(missing_modules)}")
        return 4

    print("\n[PASS] Runtime dependency validation succeeded.")
    print(f"Summary: distributions={len(required_distributions)}, modules={len(unique_module_candidates)}, missing=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
