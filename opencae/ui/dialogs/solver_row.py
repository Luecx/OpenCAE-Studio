"""Provides one solver enable/executable configuration block."""

from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from opencae.ui.core.file_path import FilePathEditor
from opencae.ui.templates import field_block


class SolverRow(QWidget):
    """Edit whether one solver is enabled and where its executable is located."""

    def __init__(self, name, config, parent=None):
        """Build one compact solver configuration block."""
        super().__init__(parent)
        self.name = str(name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.enabled = QCheckBox(f"Enable {self.name}")
        self.enabled.setChecked(bool(config.get("enabled")))
        layout.addWidget(self.enabled)

        self.path = FilePathEditor(
            str(config.get("executable", "")),
            "Executable files (*.exe);;All files (*.*)",
        )
        layout.addWidget(field_block("Executable", self.path))

    def values(self):
        """Return the persisted solver configuration represented by this row."""
        return {
            "enabled": self.enabled.isChecked(),
            "executable": self.path.text(),
            "extra_arguments": "",
        }
