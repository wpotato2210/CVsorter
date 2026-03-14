#!/usr/bin/env python3
"""Search-based static checks for protocol canonicalization and authority declarations."""

from __future__ import annotations

import hashlib
import json
import re
from ast import AnnAssign, Assign, Call, Constant, Name, Set, parse
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
PROTOCOL_COMMANDS_JSON = Path("protocol/commands.json")
OPENSPEC_COMMANDS_JSON = Path("docs/openspec/v3/protocol/commands.json")
PROTOCOL_CONSTANTS_PATH = Path("src/coloursorter/protocol/constants.py")


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


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_supported_commands_from_constants(path: Path) -> frozenset[str]:
    tree = parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    command_literals: dict[str, str] = {}
    supported_commands: set[str] | None = None

    def _assignment_target_name(node: Assign | AnnAssign) -> str | None:
        target = node.targets[0] if isinstance(node, Assign) else node.target
        if isinstance(target, Name):
            return target.id
        return None

    def _assignment_value(node: Assign | AnnAssign):
        return node.value

    for node in tree.body:
        if not isinstance(node, (Assign, AnnAssign)):
            continue
        if isinstance(node, Assign) and len(node.targets) != 1:
            continue
        target_name = _assignment_target_name(node)
        value = _assignment_value(node)
        if target_name is None or value is None:
            continue
        if target_name.startswith("CMD_") and isinstance(value, Constant) and isinstance(value.value, str):
            command_literals[target_name] = value.value
            continue
        if target_name != "SUPPORTED_COMMANDS":
            continue
        if isinstance(value, Call) and isinstance(value.func, Name) and value.func.id == "frozenset" and value.args:
            value = value.args[0]
        if not isinstance(value, Set):
            continue
        resolved_values: set[str] = set()
        for entry in value.elts:
            if isinstance(entry, Name) and entry.id in command_literals:
                resolved_values.add(command_literals[entry.id])
            elif isinstance(entry, Constant) and isinstance(entry.value, str):
                resolved_values.add(entry.value)
        supported_commands = resolved_values
    if supported_commands is None:
        raise ValueError("SUPPORTED_COMMANDS assignment was not found in constants.py")
    return frozenset(supported_commands)


def find_protocol_command_alignment_violations() -> list[Violation]:
    violations: list[Violation] = []
    if not PROTOCOL_COMMANDS_JSON.exists():
        return [Violation(path=PROTOCOL_COMMANDS_JSON, line_no=1, detail="missing protocol commands catalog")]
    if not OPENSPEC_COMMANDS_JSON.exists():
        return [Violation(path=OPENSPEC_COMMANDS_JSON, line_no=1, detail="missing openspec mirrored protocol commands catalog")]
    protocol_doc = _read_json(PROTOCOL_COMMANDS_JSON)
    openspec_doc = _read_json(OPENSPEC_COMMANDS_JSON)
    if protocol_doc != openspec_doc:
        violations.append(
            Violation(
                path=OPENSPEC_COMMANDS_JSON,
                line_no=1,
                detail=(
                    "protocol command catalog parity mismatch against protocol/commands.json"
                    f" (canonical_sha256={_sha256(PROTOCOL_COMMANDS_JSON)} mirror_sha256={_sha256(OPENSPEC_COMMANDS_JSON)})"
                ),
            )
        )

    command_set: frozenset[str] = frozenset(
        str(item["name"]) for item in protocol_doc.get("commands", []) if isinstance(item, dict) and "name" in item
    )
    constant_set = _load_supported_commands_from_constants(PROTOCOL_CONSTANTS_PATH)
    if command_set != constant_set:
        missing_in_constants = sorted(command_set - constant_set)
        extra_in_constants = sorted(constant_set - command_set)
        violations.append(
            Violation(
                path=PROTOCOL_CONSTANTS_PATH,
                line_no=1,
                detail=(
                    "SUPPORTED_COMMANDS mismatch with protocol/commands.json "
                    f"(missing_in_constants={missing_in_constants}, extra_in_constants={extra_in_constants})"
                ),
            )
        )
    return violations


def main() -> int:
    violations = [
        *find_forbidden_nack7_details(),
        *find_duplicate_protocol_authority_declarations(),
        *find_contract_schema_parity_violations(),
        *find_protocol_command_alignment_violations(),
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
