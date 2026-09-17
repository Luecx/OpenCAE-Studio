"""File-path control composed from one text input and one browse action."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.components.file_dialogs import open_file
from opencae.ui.primitives.buttons.button_inline_action import ButtonInlineAction
from opencae.ui.primitives.inputs.input_form_text import InputFormText


class ControlFilePath(QWidget):
    textChanged = pyqtSignal(str)

    def __init__(
        self,
        value: str = "",
        file_filter: str = "All files (*.*)",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.file_filter = file_filter
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.edit = InputFormText(value, object_name="CompositeFieldEdit")
        self.edit.textChanged.connect(self.textChanged)
        self.button = ButtonInlineAction(
            "…",
            tooltip="Browse",
            object_name="InlineBrowseButton",
            parent=self,
        )
        self.button.clicked.connect(self._browse)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setMinimumWidth(0)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str) -> None:
        self.edit.setText(value)

    def _browse(self) -> None:
        value = open_file(self, "Select file", self.file_filter, self.text())
        if value:
            self.setText(value)
