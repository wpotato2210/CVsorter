from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from coloursorter.eval.reject_profiles import (
    REJECTION_KEYS,
    RejectProfile,
    RejectProfileValidationError,
    load_reject_profiles,
    save_reject_profiles,
    selected_thresholds,
)

DISPLAY_LABELS: dict[str, str] = {
    "broken_snapped": "Broken/snapped",
    "immature_thin_small": "Immature/thin/small",
    "rot": "Rot",
    "mould": "Mould",
    "curliness_degrees": "Curliness (degrees)",
    "length": "Length",
    "visual_defects_spots_stripes": "Visual defects (spots/stripes)",
    "over_mature_beginning_seed_fill": "Over mature / beginning to fill seed",
}


class RejectProfileManagerWindow(QMainWindow):
    def __init__(self, config_path: str | Path = "configs/reject_profiles.yaml") -> None:
        super().__init__()
        self._config_path = Path(config_path)
        self._profiles, self._selected_name = load_reject_profiles(self._config_path)
        self._spin_boxes: dict[str, QSpinBox] = {}
        self._loading = False
        self._build_ui()
        self._refresh_profile_list()
        self._set_selected(self._selected_name)

    def active_rejection_thresholds(self) -> dict[str, float]:
        return selected_thresholds(self._profiles, self._selected_name)

    def _build_ui(self) -> None:
        self.setWindowTitle("Reject Profile Manager")
        root = QWidget(self)
        grid = QGridLayout(root)

        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_changed)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.clone_button = QPushButton("Clone")
        self.delete_button = QPushButton("Delete")
        self.select_button = QPushButton("Select Active")
        for button, callback in (
            (self.add_button, self._add_profile),
            (self.clone_button, self._clone_profile),
            (self.delete_button, self._delete_profile),
            (self.select_button, self._select_active),
        ):
            button.clicked.connect(callback)
            buttons_layout.addWidget(button)

        left_box = QGroupBox("Profiles")
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.profile_list)
        left_layout.addLayout(buttons_layout)
        left_box.setLayout(left_layout)

        form_box = QGroupBox("Thresholds (% 0-100)")
        form = QFormLayout()
        for key in REJECTION_KEYS:
            spin = QSpinBox()
            spin.setRange(0, 100)
            spin.setSingleStep(1)
            spin.valueChanged.connect(self._update_current_thresholds)
            self._spin_boxes[key] = spin
            form.addRow(QLabel(DISPLAY_LABELS[key]), spin)
        form_box.setLayout(form)

        self.active_label = QLabel("")
        self.active_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(left_box, 0, 0)
        grid.addWidget(form_box, 0, 1)
        grid.addWidget(self.active_label, 1, 0, 1, 2)

        self.setCentralWidget(root)
        self.resize(980, 480)

    def _refresh_profile_list(self) -> None:
        self.profile_list.clear()
        for profile in self._profiles:
            item = QListWidgetItem(profile.name)
            if profile.name == self._selected_name:
                item.setText(f"{profile.name} (active)")
                item.setData(Qt.ItemDataRole.UserRole, profile.name)
            else:
                item.setData(Qt.ItemDataRole.UserRole, profile.name)
            self.profile_list.addItem(item)
        self.active_label.setText(f"Active profile: {self._selected_name}")

    def _set_selected(self, profile_name: str) -> None:
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == profile_name:
                self.profile_list.setCurrentRow(i)
                return

    def _current_profile_name(self) -> str | None:
        item = self.profile_list.currentItem()
        if item is None:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))

    def _on_profile_changed(self) -> None:
        name = self._current_profile_name()
        if name is None:
            return
        profile = next(profile for profile in self._profiles if profile.name == name)
        self._loading = True
        try:
            for key, spin in self._spin_boxes.items():
                spin.setValue(int(round(profile.thresholds[key])))
        finally:
            self._loading = False

    def _update_current_thresholds(self) -> None:
        if self._loading:
            return
        name = self._current_profile_name()
        if name is None:
            return
        updated = {
            key: float(spin.value()) for key, spin in self._spin_boxes.items()
        }
        self._profiles = [
            RejectProfile(name=profile.name, thresholds=updated if profile.name == name else profile.thresholds)
            for profile in self._profiles
        ]
        self._persist()

    def _add_profile(self) -> None:
        name = self._prompt_name("New profile name")
        if name is None:
            return
        if any(profile.name == name for profile in self._profiles):
            self._error(f"Profile '{name}' already exists")
            return
        thresholds = {key: 50.0 for key in REJECTION_KEYS}
        self._profiles.append(RejectProfile(name=name, thresholds=thresholds))
        self._refresh_profile_list()
        self._set_selected(name)
        self._persist()

    def _clone_profile(self) -> None:
        source = self._current_profile_name()
        if source is None:
            return
        clone_name = self._prompt_name(f"Clone profile '{source}' as")
        if clone_name is None:
            return
        if any(profile.name == clone_name for profile in self._profiles):
            self._error(f"Profile '{clone_name}' already exists")
            return
        source_profile = next(profile for profile in self._profiles if profile.name == source)
        self._profiles.append(RejectProfile(name=clone_name, thresholds=dict(source_profile.thresholds)))
        self._refresh_profile_list()
        self._set_selected(clone_name)
        self._persist()

    def _delete_profile(self) -> None:
        name = self._current_profile_name()
        if name is None:
            return
        if len(self._profiles) == 1:
            self._error("At least one profile is required")
            return
        self._profiles = [profile for profile in self._profiles if profile.name != name]
        if self._selected_name == name:
            self._selected_name = self._profiles[0].name
        self._refresh_profile_list()
        self._set_selected(self._profiles[0].name)
        self._persist()

    def _select_active(self) -> None:
        name = self._current_profile_name()
        if name is None:
            return
        self._selected_name = name
        self._refresh_profile_list()
        self._set_selected(name)
        self._persist()

    def _persist(self) -> None:
        try:
            save_reject_profiles(self._config_path, self._profiles, self._selected_name)
        except RejectProfileValidationError as exc:
            self._error(str(exc))

    def _prompt_name(self, title: str) -> str | None:
        text, ok = QInputDialog.getText(self, title, "Name")
        cleaned = text.strip()
        if not ok or not cleaned:
            return None
        return cleaned

    def _error(self, message: str) -> None:
        QMessageBox.critical(self, "Reject Profile Manager", message)


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    window = RejectProfileManagerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
