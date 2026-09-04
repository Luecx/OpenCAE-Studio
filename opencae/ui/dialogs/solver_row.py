"""Reusable solver executable configuration block."""

from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QLineEdit, QVBoxLayout, QWidget

from opencae.ui.core.file_path import FilePathEditor
from opencae.ui.templates import apply_primary_control_height, field_block


class SolverRow(QWidget):
    """Edit whether one solver is enabled and how its process is started."""

    def __init__(self, name, config, parent=None):
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
            "Executable files (*.exe);;All files (*)",
        )
        layout.addWidget(field_block("Executable", self.path))

        self.arguments = QLineEdit(
            str(config.get("extra_arguments", config.get("arguments", "")) or "")
        )
        self.arguments.setPlaceholderText("Optional solver command-line arguments")
        apply_primary_control_height(self.arguments)
        layout.addWidget(field_block("Additional arguments", self.arguments))

    def values(self) -> dict[str, object]:
        """Return the complete backend configuration represented by this row."""
        return {
            "enabled": self.enabled.isChecked(),
            "executable": self.path.text(),
            "extra_arguments": self.arguments.text().strip(),
        }
