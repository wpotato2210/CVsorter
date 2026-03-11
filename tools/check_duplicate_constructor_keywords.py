from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CRITICAL_CONFIG_MODULES: tuple[Path, ...] = (
    Path("src/coloursorter/config/runtime.py"),
)


@dataclass(frozen=True)
class DuplicateKeyword:
    file_path: Path
    line: int
    constructor: str
    keyword: str


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "<expr>"


def _find_duplicates(file_path: Path) -> list[DuplicateKeyword]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    duplicates: list[DuplicateKeyword] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        seen: set[str] = set()
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            if keyword.arg in seen:
                duplicates.append(
                    DuplicateKeyword(
                        file_path=file_path,
                        line=keyword.lineno,
                        constructor=_call_name(node.func),
                        keyword=keyword.arg,
                    )
                )
            seen.add(keyword.arg)
    return duplicates


def _iter_paths(argv: list[str]) -> Iterable[Path]:
    if argv:
        for arg in argv:
            yield Path(arg)
        return
    yield from CRITICAL_CONFIG_MODULES


def main(argv: list[str]) -> int:
    duplicates: list[DuplicateKeyword] = []
    for path in _iter_paths(argv):
        duplicates.extend(_find_duplicates(path))

    if not duplicates:
        print("No duplicate constructor keywords found.")
        return 0

    for duplicate in duplicates:
        print(
            f"{duplicate.file_path}:{duplicate.line}: duplicate keyword '{duplicate.keyword}' "
            f"in constructor call '{duplicate.constructor}(...)'"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
