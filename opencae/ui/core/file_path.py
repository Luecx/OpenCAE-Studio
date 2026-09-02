"""Provides a reusable file-path field with a canonical inline browse action."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QToolButton, QWidget

from opencae.ui.templates import apply_inline_action_size, apply_primary_control_height
from .file_dialogs import open_file


class FilePathEditor(QWidget):
    """Edit a file path and expose a same-height browse action."""

    textChanged = pyqtSignal(str)

    def __init__(self, value: str = "", file_filter: str = "All files (*.*)", parent=None):
        """Build the path editor while keeping browse geometry consistent with selectors."""
        super().__init__(parent)
        self.file_filter = file_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.edit = QLineEdit(value)
        self.edit.setObjectName("CompositeFieldEdit")
        self.edit.setMinimumWidth(0)
        apply_primary_control_height(self.edit)
        self.edit.textChanged.connect(self.textChanged)

        self.button = QToolButton()
        self.button.setObjectName("InlineBrowseButton")
        self.button.setProperty("inlineAction", True)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setText("…")
        self.button.setToolTip("Browse")
        apply_inline_action_size(self.button)
        self.button.clicked.connect(self._browse)

        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setMinimumWidth(0)

    def text(self) -> str:
        """Return the normalized path currently shown in the editor."""
        return self.edit.text().strip()

    def setText(self, value: str) -> None:
        """Replace the currently displayed path."""
        self.edit.setText(value)

    def _browse(self) -> None:
        """Open a remembered native file chooser and adopt the selected path."""
        value = open_file(
            self,
            "Select file",
            self.file_filter,
            self.text(),
        )
        if value:
            self.setText(value)
