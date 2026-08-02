from __future__ import annotations

from PyQt6.QtCore import QProcess, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont, QFontDatabase, QTextCursor
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout


class SolverRunDialog(QDialog):
    completed = pyqtSignal(int)

    def __init__(self, title, command, working_directory, parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.resize(900, 620); self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        layout = QVBoxLayout(self); self.command = QLabel(" ".join(command)); self.command.setWordWrap(True); layout.addWidget(self.command)
        self.output = QPlainTextEdit(); self.output.setReadOnly(True); self._set_fixed_font(); layout.addWidget(self.output, 1)
        self.buttons = QDialogButtonBox(); self.stop_button = QPushButton("Stop"); self.hide_button = QPushButton("Hide")
        self.buttons.addButton(self.stop_button, QDialogButtonBox.ButtonRole.DestructiveRole); self.buttons.addButton(self.hide_button, QDialogButtonBox.ButtonRole.RejectRole)
        self.stop_button.clicked.connect(self._cancel); self.hide_button.clicked.connect(self.hide); layout.addWidget(self.buttons)
        self.process = QProcess(self); self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels); self.process.setWorkingDirectory(str(working_directory))
        self.process.readyReadStandardOutput.connect(self._read); self.process.finished.connect(self._finished)
        self.process.setProgram(command[0]); self.process.setArguments(command[1:]); self.process.start()

    def _set_fixed_font(self):
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if not font.fixedPitch(): font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace); font.setFixedPitch(True); self.output.setFont(font); self.output.document().setDefaultFont(font)
        self.output.setStyleSheet("QPlainTextEdit { font-family: Consolas, 'Courier New', monospace; }")

    def _read(self):
        text = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        if text:
            cursor = self.output.textCursor(); cursor.movePosition(QTextCursor.MoveOperation.End); self.output.setTextCursor(cursor); self.output.insertPlainText(text)

    def _cancel(self):
        if self.process.state() == QProcess.ProcessState.NotRunning: return
        self.process.terminate()
        if not self.process.waitForFinished(1500): self.process.kill()

    def _finished(self, code, _status):
        self._read(); self.output.appendPlainText(f"\nProcess finished with exit code {code}.")
        self.stop_button.setEnabled(False); self.hide_button.setText("Close"); self.completed.emit(int(code))

    def reopen(self): self.show(); self.raise_(); self.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        event.ignore(); self.hide()
