#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dist = root / "dist"
    build = root / "build"
    spec = root / "ColourSorterTestRunner.spec"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "ColourSorterTestRunner",
        "--add-data",
        f"scripts{';' if sys.platform.startswith('win') else ':'}scripts",
        "--add-data",
        f"tools{';' if sys.platform.startswith('win') else ':'}tools",
        "--add-data",
        f"configs{';' if sys.platform.startswith('win') else ':'}configs",
        "--add-data",
        f"data{';' if sys.platform.startswith('win') else ':'}data",
        "ui_test_runner/main.py",
    ]
    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=root)
    if completed.returncode != 0:
        return completed.returncode

    exe = dist / "ColourSorterTestRunner.exe"
    if exe.exists():
        print(f"Built executable: {exe}")
    else:
        print(f"Build completed; expected executable at {exe}")
    if build.exists():
        print(f"Build artifacts in {build}")
    if spec.exists():
        print(f"Spec file generated at {spec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
