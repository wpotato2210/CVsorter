from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QWidget
from shiboken6 import isValid


_UI_FILE = Path(__file__).with_name("ui_main_layout.ui")


def _is_invalid_widget(widget: QWidget | None) -> bool:
    if widget is None:
        return True
    try:
        return not isValid(widget)
    except RuntimeError:
        return True


def load_ui_main_layout(host: QMainWindow) -> QWidget:
    """Load ui_main_layout.ui and attach named widgets onto host.

    Hook points preserved for existing logic:
    - frame overlay + preview update uses host.camera_preview_label (and host.preview_label alias).
    - frame-indexed status/logging uses host.status_label.
    - start/stop/mode/serial actions use existing *_button and *_input object names.
    - BenchAppController and POCIntegration can share the same named widgets safely.
    """

    existing_central = getattr(host, "_central_widget", None)
    if not _is_invalid_widget(existing_central):
        central = existing_central
    else:
        ui_path = str(_UI_FILE)
        ui_file = QFile(ui_path)
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError(f"Unable to open UI file: {ui_path}")

        loader = QUiLoader()
        root = loader.load(ui_file)
        ui_file.close()

        if not isinstance(root, QMainWindow):
            raise TypeError("ui_main_layout.ui root widget must be a QMainWindow")

        central = root.takeCentralWidget()
        if central is None:
            raise RuntimeError("ui_main_layout.ui did not provide a central widget")

        host._ui_root_window = root
        host._central_widget = central
        host.setWindowTitle(root.windowTitle())
        host.setCentralWidget(central)

    if central is None:
        raise RuntimeError("Central widget missing during UI construction")

    if _is_invalid_widget(central) or central.parent() is None:
        raise RuntimeError("Central widget invalid before child iteration")

    for child in central.findChildren(QWidget):
        object_name = child.objectName()
        if object_name:
            setattr(host, object_name, child)

    # Keep backward compatibility with prior programmatic name in BenchMainWindow.
    host.preview_label = host.camera_preview_label

    # Keep status bar behavior from QMainWindow-based controller updates.
    host.statusBar().showMessage("Bench idle")

    return central


def load_ui(host: QMainWindow) -> QWidget:
    """Compatibility alias for load_ui()-style usage."""
    return load_ui_main_layout(host)
