"""Directory-path control composed from one text input and browse action."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QWidget

from opencae.ui.primitives.buttons.button_inline_action import ButtonInlineAction
from opencae.ui.primitives.inputs.input_form_text import InputFormText


class ControlDirectoryPath(QWidget):
    textChanged = pyqtSignal(str)

    def __init__(self, value: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.edit = InputFormText(str(value or ""), object_name="CompositeFieldEdit")
        self.edit.textChanged.connect(self.textChanged)
        self.button = ButtonInlineAction(
            "…",
            tooltip="Browse for directory",
            object_name="InlineBrowseButton",
            parent=self,
        )
        self.button.clicked.connect(self._browse)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str) -> None:
        self.edit.setText(str(value or ""))

    def _browse(self) -> None:
        initial = self.text()
        if initial:
            initial = str(Path(initial).expanduser())
        value = QFileDialog.getExistingDirectory(self, "Select directory", initial)
        if value:
            self.setText(value)
