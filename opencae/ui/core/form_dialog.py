from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from opencae.ui.templates import dialog_buttons, scaffold_dialog
from .apply_dialog import ApplyDialog
from .fields import FieldSpec, create_editor, editor_value


class FormDialog(ApplyDialog):
    def __init__(
        self,
        title: str,
        fields: tuple[FieldSpec, ...],
        parent: QWidget | None = None,
        width: int = 520,
        allow_apply: bool = False,
    ):
        super().__init__(parent)
        scaffold = scaffold_dialog(self, title, width=width, modal=True)
        self._editors = {}
        for spec in fields:
            editor = create_editor(spec)
            self._editors[spec.key] = editor
            scaffold.form.addRow(spec.label, editor)

        buttons = dialog_buttons(include_apply=allow_apply)
        self.bind_buttons(buttons, allow_apply)
        scaffold.root.addWidget(buttons)

    def values(self) -> dict:
        return {key: editor_value(widget) for key, widget in self._editors.items()}
