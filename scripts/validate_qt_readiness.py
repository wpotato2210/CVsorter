from __future__ import annotations

import os
import sys
import traceback


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:
        from PySide6.QtWidgets import QApplication

        from gui.bench_app.app import BenchMainWindow

        app = QApplication.instance() or QApplication([])
        window = BenchMainWindow()
        app.processEvents()
        window.close()
        print("PASS: BenchMainWindow constructed successfully.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: Qt readiness validation failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
