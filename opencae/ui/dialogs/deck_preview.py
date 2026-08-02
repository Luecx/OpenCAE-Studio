from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QPlainTextEdit, QVBoxLayout

from opencae.ui.core.controls import primary_button


class DeckPreviewDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Deck Preview")
        self.resize(820, 620)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title = QLabel("Input Deck Preview")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)
        editor = QPlainTextEdit(text)
        editor.setReadOnly(True)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(editor, 1)
        close = primary_button("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
