"""Provides a generic typed editor for simple scalar dataclass entity fields."""

from __future__ import annotations

from dataclasses import fields, is_dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from opencae.ui.core.fields import FieldSpec, create_editor, editor_value
from opencae.ui.templates import SectionHeading, dialog_buttons, dialog_layout, field_block


class EntityEditorDialog(QDialog):
    """Edit scalar dataclass fields when no domain-specific editor is available."""

    def __init__(self, entity, parent=None):
        """Build typed controls for editable string, integer, float and boolean fields."""
        super().__init__(parent)
        self.entity = entity
        title = f"Edit {type(entity).__name__}"
        self.setWindowTitle(title)
        self.setMinimumWidth(640)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._editors = {}

        layout = dialog_layout(self)
        layout.addWidget(SectionHeading("Properties"))
        if is_dataclass(entity):
            self._add_fields(layout, entity)
        layout.addStretch(1)

        buttons = dialog_buttons()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_fields(self, layout, entity):
        """Append supported scalar dataclass fields using the shared field factory."""
        for field in fields(entity):
            if field.name in {"id", "metadata"} or field.name.startswith("_"):
                continue
            value = getattr(entity, field.name)
            kind = _field_kind(value)
            if kind is None:
                continue
            spec = FieldSpec(field.name, field.name.replace("_", " ").title(), kind, value)
            editor = create_editor(spec)
            self._editors[field.name] = (editor, type(value))
            layout.addWidget(field_block(spec.label, editor))

    def apply(self):
        """Write normalized editor values back to the edited entity instance."""
        for name, (editor, value_type) in self._editors.items():
            value = editor_value(editor)
            if value_type is bool:
                value = bool(value)
            elif value_type in {int, float, str}:
                value = value_type(value)
            setattr(self.entity, name, value)


def _field_kind(value):
    """Return the declarative field kind for one supported scalar value."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "text"
    return None
