from __future__ import annotations

import argparse
import re
from pathlib import Path

PLACEHOLDER_PATTERNS = (
    re.compile(r"<[^>]+>"),
    re.compile(r"\[Insert[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[Specify[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[List[^\]]*\]", re.IGNORECASE),
)


def _contains_placeholder(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(pattern.search(stripped) for pattern in PLACEHOLDER_PATTERNS)


def validate_request_text(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.splitlines()

    if "REQUIREMENTS BEGIN" not in content or "REQUIREMENTS END" not in content:
        errors.append("Missing REQUIREMENTS BEGIN/END block.")
    else:
        start = lines.index(next(l for l in lines if "REQUIREMENTS BEGIN" in l))
        end = lines.index(next(l for l in lines if "REQUIREMENTS END" in l))
        if end <= start + 1:
            errors.append("REQUIREMENTS block is empty.")
        else:
            req_lines = [l.strip() for l in lines[start + 1 : end] if l.strip()]
            if not req_lines:
                errors.append("REQUIREMENTS block is empty.")
            elif len(req_lines) == 1 and req_lines[0].startswith("[") and req_lines[0].endswith("]"):
                errors.append("REQUIREMENTS block still contains placeholder text.")

    for idx, line in enumerate(lines, start=1):
        if _contains_placeholder(line):
            errors.append(f"Line {idx} contains unresolved placeholder: {line.strip()}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that an implementation request prompt has concrete requirements."
    )
    parser.add_argument("request_file", type=Path, help="Path to a text/markdown request file")
    args = parser.parse_args()

    content = args.request_file.read_text(encoding="utf-8")
    errors = validate_request_text(content)

    if errors:
        print("Implementation request validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Implementation request validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
