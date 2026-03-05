#!/usr/bin/env python3
"""CI smoke imports for native dependency validation.

Purpose: catch missing native shared libraries (for example ``libGL.so.1`` for OpenCV)
early in minimal CI/container environments before runtime entry points fail.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from typing import List


CRITICAL_MODULES: tuple[str, ...] = ("cv2", "numpy")
OPTIONAL_MODULES_IF_PRESENT: tuple[str, ...] = ("torch",)


def _import_or_error(module_name: str) -> str | None:
    """Import module_name and return an actionable error message on failure."""
    try:
        importlib.import_module(module_name)
        return None
    except Exception as exc:  # pragma: no cover - smoke-level safety net
        return (
            f"[FAIL] import {module_name!r}: {exc}\n"
            "Action: ensure required OS-level native libraries are installed "
            "(e.g. libGL/libglib for OpenCV) and Python deps are pinned for CI."
        )


def main() -> int:
    errors: List[str] = []

    for module_name in CRITICAL_MODULES:
        maybe_error = _import_or_error(module_name)
        if maybe_error:
            errors.append(maybe_error)

    for module_name in OPTIONAL_MODULES_IF_PRESENT:
        if importlib.util.find_spec(module_name) is None:
            print(f"[SKIP] optional module {module_name!r} not installed")
            continue
        maybe_error = _import_or_error(module_name)
        if maybe_error:
            errors.append(maybe_error)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print("[OK] smoke imports passed: cv2, numpy (+ torch when installed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
