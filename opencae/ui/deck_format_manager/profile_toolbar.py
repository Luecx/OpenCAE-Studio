"""Provides the profile-management toolbar for the deck-format editor."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QInputDialog, QWidget

from opencae.ui.core.fields import FieldSpec, create_editor
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    ButtonRole,
    ButtonSpec,
    apply_primary_control_height,
    button,
    label,
)


class DeckProfileToolbar(QWidget):
    """Select immutable built-ins and persisted editable deck-profile copies."""

    save_requested = pyqtSignal()
    selection_changed = pyqtSignal()
    profile_copied = pyqtSignal(str, str)
    profile_created = pyqtSignal(str, str)
    profile_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profile_meta: dict[str, tuple[str, bool]] = {
            "FEMaster": ("FEMaster", True),
            "Abaqus": ("Abaqus", True),
            "CalculiX": ("CalculiX", True),
        }

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(label("Profile:"))

        profile = create_editor(
            FieldSpec(
                "profile",
                "Profile",
                kind="choice",
                choices=tuple(self._profile_meta),
                default="FEMaster",
            )
        )
        if not isinstance(profile, ChevronComboBox):
            raise TypeError("Deck profile selector must use ChevronComboBox")
        self.profile_combo = profile
        self.profile_combo.setMinimumWidth(340)
        layout.addWidget(self.profile_combo, 1)

        self.new_button = self._button(
            "New Profile",
            IconKind.FILE,
            self._new_profile,
            "Create an editable profile based on the selected format.",
        )
        self.copy_button = self._button(
            "Copy",
            IconKind.DUPLICATE,
            self.copy_profile,
            "Copy the selected profile into an editable user profile.",
        )
        self.delete_button = self._button(
            "Delete",
            IconKind.DELETE,
            self.delete_profile,
            "Delete the selected user profile.",
            role=ButtonRole.DANGER,
        )
        self.save_button = self._button(
            "Save",
            IconKind.SAVE,
            self.save_requested.emit,
            "Save changes to the selected user profile.",
        )
        for control in (
            self.new_button,
            self.copy_button,
            self.delete_button,
            self.save_button,
        ):
            layout.addWidget(control)

        self.profile_combo.currentTextChanged.connect(self._selection_changed)
        self._refresh_actions()

    def profile_name(self) -> str:
        return self.profile_combo.currentText()

    def format_name(self) -> str:
        return self._profile_meta.get(self.profile_name(), ("FEMaster", True))[0]

    def is_builtin(self) -> bool:
        return self._profile_meta.get(self.profile_name(), ("", False))[1]

    def is_editable(self) -> bool:
        return bool(self.profile_name()) and not self.is_builtin()

    def register_profile(self, name: str, format_name: str) -> bool:
        """Register one persisted editable profile without changing selection."""
        name = str(name).strip()
        format_name = str(format_name).strip()
        if not name or not format_name or name in self._profile_meta:
            return False
        self._profile_meta[name] = (format_name, False)
        self.profile_combo.addItem(name)
        self._refresh_actions()
        return True

    def set_profile(self, name: str) -> bool:
        """Select a known built-in or user profile by name."""
        if name not in self._profile_meta:
            return False
        self.profile_combo.setCurrentText(name)
        return True

    def profile_names(self) -> tuple[str, ...]:
        """Return profile names in selector order."""
        return tuple(
            self.profile_combo.itemText(index)
            for index in range(self.profile_combo.count())
        )

    def copy_profile(self) -> str:
        source = self.profile_name() or "FEMaster"
        candidate = self._unique_name(source + " Copy")
        self._profile_meta[candidate] = (self.format_name(), False)
        self.profile_combo.addItem(candidate)
        self.profile_copied.emit(source, candidate)
        self.profile_combo.setCurrentText(candidate)
        return candidate

    def delete_profile(self) -> None:
        name = self.profile_name()
        if not name or self.is_builtin():
            return
        index = self.profile_combo.currentIndex()
        self._profile_meta.pop(name, None)
        self.profile_combo.removeItem(index)
        self.profile_deleted.emit(name)
        self._refresh_actions()

    def _button(
        self,
        text: str,
        icon_kind: IconKind,
        callback,
        tooltip: str,
        *,
        role: ButtonRole = ButtonRole.DEFAULT,
    ):
        control = button(
            ButtonSpec(
                text,
                role=role,
                tooltip=tooltip,
                icon=make_icon(icon_kind, 18),
            ),
            clicked=callback,
        )
        return apply_primary_control_height(control)

    def _new_profile(self) -> None:
        base_format = self.format_name()
        default_name = self._unique_name(base_format + " - Custom")
        name, ok = QInputDialog.getText(
            self,
            "New Profile",
            "Profile name:",
            text=default_name,
        )
        if not ok or not name.strip():
            return
        profile = name.strip()
        if profile in self._profile_meta:
            profile = self._unique_name(profile)
        self._profile_meta[profile] = (base_format, False)
        self.profile_combo.addItem(profile)
        self.profile_created.emit(profile, base_format)
        self.profile_combo.setCurrentText(profile)

    def _unique_name(self, base: str) -> str:
        if base not in self._profile_meta:
            return base
        number = 2
        while f"{base} {number}" in self._profile_meta:
            number += 1
        return f"{base} {number}"

    def _selection_changed(self, _name: str) -> None:
        self._refresh_actions()
        self.selection_changed.emit()

    def _refresh_actions(self) -> None:
        editable = self.is_editable()
        self.delete_button.setEnabled(editable)
        self.save_button.setEnabled(editable)
        self.copy_button.setEnabled(bool(self.profile_name()))
