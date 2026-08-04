from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont, QFontDatabase, QTextCursor
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout


class TopologyRunDialog(QDialog):
    stop_requested = pyqtSignal()

    def __init__(self, title, directory, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(920, 640)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        layout = QVBoxLayout(self)
        label = QLabel(f"Working directory: {directory}")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(20000)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if not font.fixedPitch(): font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace); font.setFixedPitch(True)
        self.output.setFont(font)
        layout.addWidget(self.output, 1)
        buttons = QDialogButtonBox()
        self.stop_button = QPushButton("Stop")
        self.hide_button = QPushButton("Hide")
        buttons.addButton(self.stop_button, QDialogButtonBox.ButtonRole.DestructiveRole)
        buttons.addButton(self.hide_button, QDialogButtonBox.ButtonRole.RejectRole)
        self.stop_button.clicked.connect(self.stop_requested)
        self.hide_button.clicked.connect(self.hide)
        layout.addWidget(buttons)

    def append(self, text):
        if not str(text).strip(): return
        cursor = self.output.textCursor(); cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output.setTextCursor(cursor); self.output.insertPlainText(str(text).rstrip() + "\n")

    def complete(self, status):
        self.append(f"Optimization finished: {status}")
        self.stop_button.setEnabled(False)
        self.hide_button.setText("Close")

    def reopen(self):
        self.show(); self.raise_(); self.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        event.ignore(); self.hide()
