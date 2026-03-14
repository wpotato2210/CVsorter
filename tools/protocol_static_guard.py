#!/usr/bin/env python3
"""Search-based static checks for protocol canonicalization and authority declarations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

SCAN_ROOTS = (
    Path("src"),
    Path("tests"),
    Path("tools"),
    Path("protocol"),
    Path("docs/openspec/v3"),
)
SKIP_PARTIALS = ("/.git/", "__pycache__")
SCANNED_SUFFIXES = {".py", ".json", ".yml", ".yaml"}
FORBIDDEN_NACK7_RE = re.compile(r"NACK\|7\|([A-Z_]+)")
AUTHORITY_ASSIGN_RE = re.compile(r"^\s*AUTHORITATIVE_PROTOCOL_JSON(?:\s*:[^=]+)?\s*=")
AUTHORITY_PATH = Path("src/coloursorter/protocol/authority.py")
CONTRACT_CANONICAL_DIR = Path("contracts")
CONTRACT_MIRROR_DIR = Path("docs/openspec/v3/contracts")
CONTRACT_PARITY_FILES = (
    "frame_schema.json",
    "mcu_response_schema.json",
    "mcu_response_schema_strict.json",
    "sched_schema.json",
)


@dataclass(frozen=True)
class Violation:
    path: Path
    line_no: int
    detail: str


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            normalized = f"/{path.as_posix()}"
            if any(token in normalized for token in SKIP_PARTIALS):
                continue
            if path.suffix not in SCANNED_SUFFIXES:
                continue
            files.append(path)
    return files


def find_forbidden_nack7_details() -> list[Violation]:
    violations: list[Violation] = []
    for path in _iter_files():
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            for match in FORBIDDEN_NACK7_RE.finditer(line):
                if match.group(1) != "BUSY":
                    violations.append(Violation(path=path, line_no=line_no, detail=f"forbidden NACK|7| detail '{match.group(1)}'"))
    return violations


def find_duplicate_protocol_authority_declarations() -> list[Violation]:
    declarations: list[Violation] = []
    for path in _iter_files():
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if AUTHORITY_ASSIGN_RE.search(line):
                declarations.append(Violation(path=path, line_no=line_no, detail="AUTHORITATIVE_PROTOCOL_JSON declaration"))

    if len(declarations) == 1 and declarations[0].path == AUTHORITY_PATH:
        return []

    if not declarations:
        return [Violation(path=AUTHORITY_PATH, line_no=1, detail="missing AUTHORITATIVE_PROTOCOL_JSON declaration")]

    return [
        Violation(path=decl.path, line_no=decl.line_no, detail="duplicate/invalid AUTHORITATIVE_PROTOCOL_JSON declaration")
        for decl in declarations
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_contract_schema_parity_violations() -> list[Violation]:
    violations: list[Violation] = []
    for filename in CONTRACT_PARITY_FILES:
        canonical_path = CONTRACT_CANONICAL_DIR / filename
        mirror_path = CONTRACT_MIRROR_DIR / filename
        if not canonical_path.exists():
            violations.append(
                Violation(path=canonical_path, line_no=1, detail="missing canonical contract schema in contracts/")
            )
            continue
        if not mirror_path.exists():
            violations.append(
                Violation(path=mirror_path, line_no=1, detail="missing mirrored contract schema in docs/openspec/v3/contracts/")
            )
            continue
        canonical_hash = _sha256(canonical_path)
        mirror_hash = _sha256(mirror_path)
        if canonical_hash != mirror_hash:
            violations.append(
                Violation(
                    path=mirror_path,
                    line_no=1,
                    detail=(
                        "contract schema parity mismatch against canonical contracts/"
                        f" ({filename} canonical_sha256={canonical_hash} mirror_sha256={mirror_hash})"
                    ),
                )
            )
    return violations


def main() -> int:
    violations = [
        *find_forbidden_nack7_details(),
        *find_duplicate_protocol_authority_declarations(),
        *find_contract_schema_parity_violations(),
    ]
    if violations:
        print("Protocol static guard: FAIL")
        for violation in violations:
            print(f"- {violation.path}:{violation.line_no}: {violation.detail}")
        return 1
    print("Protocol static guard: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
