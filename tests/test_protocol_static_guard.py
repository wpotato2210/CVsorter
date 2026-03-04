from __future__ import annotations

import subprocess
import sys


def test_protocol_static_guard_passes() -> None:
    result = subprocess.run(
        [sys.executable, "tools/protocol_static_guard.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
