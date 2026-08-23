"""Provides the standard label-above shell for named create/edit dialogs."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QLineEdit, QMessageBox

from opencae.model.naming import is_unique
from opencae.ui.templates import (
    apply_primary_control_height,
    dialog_buttons,
    scaffold_dialog,
)

from .apply_dialog import ApplyDialog


class NamedEntityDialog(ApplyDialog):
    """Reusable named-entity dialog with canonical fields and standard buttons."""

    def __init__(
        self,
        title,
        value,
        *,
        existing_names=(),
        parent=None,
        width=520,
    ):
        """Build the common name field and leave room for subclass-specific content."""
        super().__init__(parent)
        self.value = deepcopy(value)
        self._existing_names = tuple(existing_names)
        self._current_name = str(getattr(value, "name", ""))

        scaffold = scaffold_dialog(self, title, width=int(width), modal=False)
        self.root = scaffold.root
        self.form = scaffold.form
        self.name = QLineEdit(self._current_name)
        apply_primary_control_height(self.name)
        self.form.addRow("Name", self.name)

        self.buttons = dialog_buttons(include_apply=False)
        self._finished_layout = False

    def add_widget(self, widget):
        """Append one specialized widget below the canonical field stack."""
        self.root.addWidget(widget)
        return widget

    def finish(self):
        """Bind and append standard buttons exactly once."""
        if self._finished_layout:
            return
        self._finished_layout = True
        self.bind_buttons(self.buttons, allow_apply=False)
        self.root.addWidget(self.buttons)

    def apply_name(self, candidate):
        """Copy the edited display name onto a candidate entity."""
        candidate.name = self.name.text().strip()
        return candidate

    def validate(self) -> bool:
        """Require a non-empty name unique within the supplied scope."""
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Enter a name.")
            return False
        if not is_unique(name, self._existing_names, self._current_name):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"An object named '{name}' already exists in this scope.",
            )
            return False
        return True
