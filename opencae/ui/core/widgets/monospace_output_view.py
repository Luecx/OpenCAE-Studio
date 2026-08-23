"""Read-only high-volume output widget with the system monospace font."""

from PyQt6.QtGui import QFontDatabase, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit


class MonospaceOutputView(QPlainTextEdit):
    """Present bounded solver or application output inside a dedicated view."""

    def __init__(self, parent=None):
        """Build a read-only no-wrap text surface suitable for long transcripts."""
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.document().setMaximumBlockCount(50000)

    def set_output(self, text):
        """Replace the transcript and keep the viewport scrolled to its end."""
        self.setPlainText(str(text or ""))
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
