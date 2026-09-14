"""Provides a reusable directory-path field with an inline browse action."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QWidget

from opencae.ui.primitives.buttons import InlineButton
from opencae.ui.templates import apply_primary_control_height


class DirectoryPathEditor(QWidget):
    """Edit a directory path using the same compact composite-field geometry as files."""

    textChanged = pyqtSignal(str)

    def __init__(self, value: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.edit = QLineEdit(str(value or ""))
        self.edit.setObjectName("CompositeFieldEdit")
        self.edit.setMinimumWidth(0)
        apply_primary_control_height(self.edit)
        self.edit.textChanged.connect(self.textChanged)

        self.button = InlineButton(
            "…",
            tooltip="Browse for directory",
            object_name="InlineBrowseButton",
            parent=self,
        )
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self._browse)

        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)

    def text(self) -> str:
        """Return the normalized directory currently shown in the editor."""
        return self.edit.text().strip()

    def setText(self, value: str) -> None:
        """Replace the displayed directory path."""
        self.edit.setText(str(value or ""))

    def _browse(self) -> None:
        """Choose an existing directory and preserve the current text on cancellation."""
        initial = self.text()
        if initial:
            initial = str(Path(initial).expanduser())
        value = QFileDialog.getExistingDirectory(self, "Select directory", initial)
        if value:
            self.setText(value)
