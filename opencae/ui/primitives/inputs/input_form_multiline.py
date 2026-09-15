"""Canonical multiline text editor for forms and dialogs."""

from PyQt6.QtWidgets import QPlainTextEdit, QWidget


class InputFormMultiline(QPlainTextEdit):
    def __init__(
        self,
        text: str = "",
        *,
        placeholder: str = "",
        read_only: bool = False,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setPlainText(str(text))
        self.setReadOnly(bool(read_only))
        if placeholder:
            self.setPlaceholderText(str(placeholder))
        if object_name:
            self.setObjectName(object_name)
