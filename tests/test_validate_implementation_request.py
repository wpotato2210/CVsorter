from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path("tools/validate_implementation_request.py")


def _run_validator(request_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(request_path)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_validator_rejects_placeholder_request(tmp_path: Path) -> None:
    request_path = tmp_path / "request.md"
    request_path.write_text(
        """
# PROJECT: [Insert brief project description and goals here]
# MODULE: [Insert module/function name or path]
# LANGUAGE: [Specify language]

# REQUIREMENTS BEGIN
[Describe specific feature/behavior]
# REQUIREMENTS END
""".strip(),
        encoding="utf-8",
    )

    result = _run_validator(request_path)

    assert result.returncode == 1
    assert "placeholder" in (result.stdout + result.stderr).lower()


def test_validator_accepts_concrete_request(tmp_path: Path) -> None:
    request_path = tmp_path / "request.md"
    request_path.write_text(
        """
# PROJECT: Add runtime calibration checksum verification.
# MODULE: src/coloursorter/runtime/config.py
# LANGUAGE: Python

# REQUIREMENTS BEGIN
Implement checksum verification for calibration files loaded at startup.
Return a descriptive ValueError when checksum mismatches.
Add tests for valid and invalid checksum payloads.
# REQUIREMENTS END
""".strip(),
        encoding="utf-8",
    )

    result = _run_validator(request_path)

    assert result.returncode == 0, result.stdout + result.stderr
