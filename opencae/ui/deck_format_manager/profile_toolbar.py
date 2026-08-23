"""Provides the format/profile management toolbar for the editor prototype."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QWidget,
)

from opencae.ui.core.icon_factory import IconKind, make_icon


class DeckProfileToolbar(QWidget):
    """Manage temporary format/profile selections above the deck editor."""

    save_requested = pyqtSignal()
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Build built-in format/profile selectors and management actions."""
        super().__init__(parent)
        self._profiles = {
            "FEMaster": ["FEMaster - Default", "FEMaster - Custom"],
            "Abaqus": ["Abaqus - Default"],
        }
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Built-in Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(tuple(self._profiles))
        self.format_combo.setMinimumWidth(190)
        layout.addWidget(self.format_combo)
        layout.addSpacing(12)
        layout.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(260)
        layout.addWidget(self.profile_combo, 1)

        for button in (
            self._button("New Profile", IconKind.FILE, self._new_profile),
            self._button("Copy", IconKind.DUPLICATE, self._copy_profile),
            self._button("Delete", IconKind.DELETE, self._delete_profile),
            self._button("Save", IconKind.SAVE, self.save_requested.emit),
        ):
            layout.addWidget(button)

        self.format_combo.currentTextChanged.connect(self._format_changed)
        self.profile_combo.currentTextChanged.connect(
            lambda _text: self.selection_changed.emit()
        )
        self._format_changed(self.format_combo.currentText())

    def format_name(self) -> str:
        """Return the selected built-in format name."""
        return self.format_combo.currentText()

    def profile_name(self) -> str:
        """Return the selected editable profile name."""
        return self.profile_combo.currentText()

    @staticmethod
    def _button(text: str, icon: IconKind, callback) -> QPushButton:
        """Create one compact profile toolbar button."""
        button = QPushButton(text)
        button.setIcon(make_icon(icon, 18))
        button.clicked.connect(callback)
        return button

    def _format_changed(self, name: str) -> None:
        """Refresh profiles when the built-in format selection changes."""
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self._profiles.get(name, ()))
        self.profile_combo.blockSignals(False)
        self.selection_changed.emit()

    def _new_profile(self) -> None:
        """Create a session-only profile for evaluating the management workflow."""
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if not ok or not name.strip():
            return
        profile = name.strip()
        values = self._profiles.setdefault(self.format_name(), [])
        if profile not in values:
            values.append(profile)
            self.profile_combo.addItem(profile)
        self.profile_combo.setCurrentText(profile)

    def _copy_profile(self) -> None:
        """Copy the current profile inside the editor session."""
        current = self.profile_name() or "Profile"
        values = self._profiles.setdefault(self.format_name(), [])
        base = current + " Copy"
        candidate = base
        number = 2
        while candidate in values:
            candidate = f"{base} {number}"
            number += 1
        values.append(candidate)
        self.profile_combo.addItem(candidate)
        self.profile_combo.setCurrentText(candidate)

    def _delete_profile(self) -> None:
        """Delete user profiles while keeping the built-in default profile."""
        index = self.profile_combo.currentIndex()
        if index <= 0:
            return
        values = self._profiles.get(self.format_name(), [])
        if index < len(values):
            values.pop(index)
        self.profile_combo.removeItem(index)
        self.selection_changed.emit()
