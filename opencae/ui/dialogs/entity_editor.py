from __future__ import annotations

from dataclasses import fields, is_dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QVBoxLayout

from opencae.ui.core.controls import dialog_buttons


class EntityEditorDialog(QDialog):
    def __init__(self, entity, parent=None):
        super().__init__(parent)
        self.entity = entity
        title = f"Edit {type(entity).__name__}"
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._editors = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("PanelTitle")
        layout.addWidget(heading)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        if is_dataclass(entity):
            self._add_fields(form, entity)
        layout.addLayout(form)
        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_fields(self, form, entity):
        for field in fields(entity):
            if field.name in {"id", "metadata"}:
                continue
            value = getattr(entity, field.name)
            if isinstance(value, (str, int, float, bool)):
                editor = QLineEdit(str(value))
                self._editors[field.name] = (editor, type(value))
                form.addRow(field.name.replace("_", " ").title(), editor)

    def apply(self):
        for name, (editor, value_type) in self._editors.items():
            text = editor.text().strip()
            if value_type is bool:
                value = text.lower() in {"true", "1", "yes", "on"}
            else:
                try:
                    value = value_type(text)
                except ValueError:
                    value = text
            setattr(self.entity, name, value)
