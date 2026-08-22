"""Provides the standard form shell for named create/edit dialogs."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QLineEdit, QMessageBox

from opencae.model.naming import is_unique
from opencae.ui.templates import dialog_buttons, scaffold_dialog

from .apply_dialog import ApplyDialog


class NamedEntityDialog(ApplyDialog):
    """Reusable dialog layout with heading, name field and standard buttons."""

    def __init__(
        self,
        title,
        value,
        *,
        existing_names=(),
        parent=None,
        width=520,
    ):
        super().__init__(parent)
        self.value = deepcopy(value)
        self._existing_names = tuple(existing_names)
        self._current_name = str(getattr(value, "name", ""))

        scaffold = scaffold_dialog(self, title, width=int(width), modal=False)
        self.root = scaffold.root
        self.form = scaffold.form
        self.name = QLineEdit(self._current_name)
        self.form.addRow("Name", self.name)

        self.buttons = dialog_buttons(include_apply=False)
        self._finished_layout = False

    def add_widget(self, widget):
        self.root.addWidget(widget)
        return widget

    def finish(self):
        if self._finished_layout:
            return
        self._finished_layout = True
        self.bind_buttons(self.buttons, allow_apply=False)
        self.root.addWidget(self.buttons)

    def apply_name(self, candidate):
        candidate.name = self.name.text().strip()
        return candidate

    def validate(self) -> bool:
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
