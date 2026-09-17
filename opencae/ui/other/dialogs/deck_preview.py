"""Provides a read-only preview of generated solver input decks."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QPlainTextEdit

from opencae.ui.primitives.buttons import ButtonFormPrimary
from opencae.ui.primitives.inputs import InputFormMultiline
from opencae.ui.primitives.labels import LabelTitle
from opencae.ui.components.layouts import dialog_layout

class DeckPreviewDialog(QDialog):
    """Display generated input text without wrapping or editing it."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Deck Preview")
        self.resize(820, 620)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = dialog_layout(self)
        layout.addWidget(LabelTitle("Input Deck Preview"))
        editor = InputFormMultiline(text, read_only=True)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(editor, 1)

        close = ButtonFormPrimary("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
