from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QWidget

from opencae.ui.templates import apply_close_buttons, scaffold_dialog
from .fields import FieldSpec, create_editor, editor_value


class ApplyFormDialog(QDialog):
    apply_requested = pyqtSignal(object)

    def __init__(
        self,
        title: str,
        fields: tuple[FieldSpec, ...],
        parent: QWidget | None = None,
        width: int = 520,
    ):
        super().__init__(parent)
        scaffold = scaffold_dialog(
            self,
            title,
            width=width,
            modal=False,
            delete_on_close=True,
        )
        self._editors = {}
        for spec in fields:
            editor = create_editor(spec)
            self._editors[spec.key] = editor
            scaffold.form.addRow(spec.label, editor)

        buttons = apply_close_buttons()
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if close_button is not None:
            close_button.clicked.connect(self.close)
        if apply_button is not None:
            apply_button.clicked.connect(lambda: self.apply_requested.emit(self.values()))
        scaffold.root.addWidget(buttons)

    def values(self) -> dict:
        return {key: editor_value(widget) for key, widget in self._editors.items()}
