from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox


class ApplyDialog(QDialog):
    """QDialog with a validated, non-closing Apply action."""

    applied = pyqtSignal()

    def validate(self) -> bool:
        return True

    def accept(self) -> None:
        if self.validate():
            super().accept()

    def request_apply(self) -> None:
        if self.validate():
            self.applied.emit()

    def bind_buttons(self, buttons: QDialogButtonBox, allow_apply: bool = True) -> None:
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        if allow_apply:
            apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
            if apply_button is not None:
                apply_button.clicked.connect(self.request_apply)
