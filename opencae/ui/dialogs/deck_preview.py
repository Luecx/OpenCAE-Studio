"""Provides a read-only preview of generated solver input decks."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QPlainTextEdit

from opencae.ui.core.controls import primary_button
from opencae.ui.templates import LabelRole, dialog_layout, label


class DeckPreviewDialog(QDialog):
    """Display generated input text without wrapping or editing it."""

    def __init__(self, text: str, parent=None):
        """Build the preview using the canonical dialog spacing and title style."""
        super().__init__(parent)
        self.setWindowTitle("Input Deck Preview")
        self.resize(820, 620)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = dialog_layout(self)
        layout.addWidget(label("Input Deck Preview", role=LabelRole.TITLE))
        editor = QPlainTextEdit(text)
        editor.setReadOnly(True)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(editor, 1)

        close = primary_button("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
