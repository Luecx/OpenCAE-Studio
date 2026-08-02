from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QToolButton, QWidget


class FilePathEditor(QWidget):
    textChanged = pyqtSignal(str)

    def __init__(self, value: str = "", file_filter: str = "All files (*.*)", parent=None):
        super().__init__(parent)
        self.file_filter = file_filter
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.edit = QLineEdit(value)
        self.edit.setObjectName("CompositeFieldEdit")
        self.edit.textChanged.connect(self.textChanged)
        self.button = QToolButton()
        self.button.setFixedSize(30, 30)
        self.button.setText("…")
        self.button.setToolTip("Browse")
        self.button.clicked.connect(self._browse)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button)
        self.setMinimumWidth(316)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str) -> None:
        self.edit.setText(value)

    def _browse(self) -> None:
        value, _ = QFileDialog.getOpenFileName(self, "Select file", self.text(), self.file_filter)
        if value:
            self.setText(value)
