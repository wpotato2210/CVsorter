from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_dependency_sync_guard_passes_for_repo_files() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/sync_requirements.py", "--check"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_dependency_sync_guard_detects_divergence(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    requirements_path = tmp_path / "requirements.txt"

    pyproject_path.write_text(
        """
[project]
dependencies = [
  "numpy>=1.0,<2.0",
]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    requirements_path.write_text("numpy>=2.0\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/sync_requirements.py",
            "--check",
            "--pyproject",
            str(pyproject_path),
            "--requirements",
            str(requirements_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "expected(requirements from pyproject)" in result.stdout
