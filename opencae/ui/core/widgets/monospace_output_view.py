"""Read-only high-volume output widget with the system monospace font."""

from PyQt6.QtGui import QFontDatabase, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit


class MonospaceOutputView(QPlainTextEdit):
    """Central log presentation used for every selected job."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.document().setMaximumBlockCount(50000)

    def set_output(self, text):
        self.setPlainText(str(text or ""))
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
