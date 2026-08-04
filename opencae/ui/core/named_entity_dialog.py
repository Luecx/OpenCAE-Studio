"""Provides the standard modeless form shell for named create/edit dialogs."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique

from .apply_dialog import ApplyDialog
from .controls import dialog_buttons


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
        self.setWindowTitle(title)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(int(width))

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(18, 16, 18, 14)
        self.root.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("PanelTitle")
        self.root.addWidget(heading)

        self.form = QFormLayout()
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setHorizontalSpacing(18)
        self.form.setVerticalSpacing(10)
        self.form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        self.name = QLineEdit(self._current_name)
        self.form.addRow("Name", self.name)
        self.root.addLayout(self.form)

        self.buttons = dialog_buttons(include_apply=False)
        self._finished_layout = False

    def add_widget(self, widget):
        """Append a custom section below the standard name form."""

        self.root.addWidget(widget)
        return widget

    def finish(self):
        """Append and bind the standard OK/Cancel buttons exactly once."""

        if self._finished_layout:
            return
        self._finished_layout = True
        self.bind_buttons(self.buttons, allow_apply=False)
        self.root.addWidget(self.buttons)

    def apply_name(self, candidate):
        """Copy the normalized dialog name onto a candidate entity."""

        candidate.name = self.name.text().strip()
        return candidate

    def validate(self) -> bool:
        """Validate the shared name field before accepting the dialog."""

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
