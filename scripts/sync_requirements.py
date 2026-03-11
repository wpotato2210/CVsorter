#!/usr/bin/env python3
"""Synchronize requirements.txt with runtime dependencies in pyproject.toml."""

from __future__ import annotations

import argparse
import difflib
from pathlib import Path
from typing import Sequence

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - py<3.11 fallback
    from pip._vendor import tomli as tomllib  # type: ignore[no-redef]

HEADER: str = "# Auto-generated from pyproject.toml by scripts/sync_requirements.py\n"


def load_runtime_dependencies(pyproject_path: Path) -> list[str]:
    """Return [project.dependencies] in declared order."""
    data: dict[str, object] = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project: dict[str, object] = data.get("project", {})  # type: ignore[assignment]
    dependencies: list[str] = project.get("dependencies", [])  # type: ignore[assignment]
    return list(dependencies)


def render_requirements(dependencies: Sequence[str]) -> str:
    body: str = "\n".join(dependencies)
    return f"{HEADER}{body}\n"


def check_sync(pyproject_path: Path, requirements_path: Path) -> int:
    expected: str = render_requirements(load_runtime_dependencies(pyproject_path))
    current: str = requirements_path.read_text(encoding="utf-8")
    if current == expected:
        return 0
    diff: str = "\n".join(
        difflib.unified_diff(
            current.splitlines(),
            expected.splitlines(),
            fromfile=str(requirements_path),
            tofile="expected(requirements from pyproject)",
            lineterm="",
        )
    )
    print(diff)
    return 1


def write_sync(pyproject_path: Path, requirements_path: Path) -> int:
    rendered: str = render_requirements(load_runtime_dependencies(pyproject_path))
    requirements_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {requirements_path} from {pyproject_path}.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--requirements", type=Path, default=Path("requirements.txt"))
    parser.add_argument("--check", action="store_true", help="Fail if not synchronized.")
    return parser.parse_args()


def main() -> int:
    args: argparse.Namespace = parse_args()
    if args.check:
        return check_sync(args.pyproject, args.requirements)
    return write_sync(args.pyproject, args.requirements)


if __name__ == "__main__":
    raise SystemExit(main())
