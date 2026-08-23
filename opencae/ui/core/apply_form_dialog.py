"""Provides a standardized modeless form with Apply, OK, and Cancel semantics."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QWidget

from opencae.ui.templates import dialog_buttons, scaffold_dialog
from .fields import FieldSpec, create_editor, editor_value


class ApplyFormDialog(QDialog):
    """Modeless form where Apply commits in place and OK commits then closes."""

    apply_requested = pyqtSignal(object)

    def __init__(
        self,
        title: str,
        fields: tuple[FieldSpec, ...],
        parent: QWidget | None = None,
        width: int = 520,
    ):
        """Build the canonical editable field stack and three-action button row."""
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

        buttons = dialog_buttons(include_apply=True)
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._emit_apply)
        buttons.accepted.connect(self._accept_with_apply)
        buttons.rejected.connect(self.reject)
        scaffold.root.addWidget(buttons)

    def _emit_apply(self) -> None:
        """Emit the current values without closing the dialog."""
        self.apply_requested.emit(self.values())

    def _accept_with_apply(self) -> None:
        """Commit the current values once and close with Accepted."""
        self._emit_apply()
        self.accept()

    def values(self) -> dict:
        """Return the current editor values keyed by field specification."""
        return {
            key: editor_value(widget)
            for key, widget in self._editors.items()
        }
