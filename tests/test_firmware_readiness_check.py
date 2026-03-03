from __future__ import annotations

import subprocess
import sys


def test_firmware_readiness_check_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, "tools/firmware_readiness_check.py", "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
