"""Fail if malformed directive wrappers or corrupted typography appear in key markdown docs."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Iterable

TARGET_FILES: tuple[str, ...] = (
    "testing_strategy.md",
    "TESTING.md",
)

# Wrapper syntax seen in malformed generated docs and typography artifacts.
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (":::writing{", "non-standard directive wrapper marker"),
    ("“", "smart opening quote"),
    ("”", "smart closing quote"),
    ("⸻", "corrupted horizontal separator glyph"),
)


def iter_violations(text: str) -> Iterable[tuple[int, str, str]]:
    """Yield (line_number, token, reason) for forbidden patterns in text."""
    for line_no, line in enumerate(text.splitlines(), start=1):
        for token, reason in FORBIDDEN_PATTERNS:
            if token in line:
                yield line_no, token, reason


def main() -> int:
    root: Path = Path(__file__).resolve().parents[1]
    has_error: bool = False

    for rel_path in TARGET_FILES:
        file_path: Path = root / rel_path
        if not file_path.exists():
            print(f"ERROR: required docs file not found: {rel_path}")
            has_error = True
            continue

        text: str = file_path.read_text(encoding="utf-8")
        for line_no, token, reason in iter_violations(text):
            print(f"ERROR: {rel_path}:{line_no}: forbidden token {token!r} ({reason})")
            has_error = True

    if has_error:
        print("Docs wrapper lint: FAILED")
        return 1

    print("Docs wrapper lint: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
