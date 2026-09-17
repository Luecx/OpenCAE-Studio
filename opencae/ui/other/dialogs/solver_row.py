"""Reusable solver executable configuration block."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.ui.components.controls import ControlFilePath
from opencae.ui.primitives.checks import CheckForm
from opencae.ui.primitives.inputs import InputFormText
from opencae.ui.components.form_field import FormField

class SolverRow(QWidget):
    """Edit whether one solver is enabled and how its process is started."""

    def __init__(self, name, config, parent=None):
        super().__init__(parent)
        self.name = str(name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.enabled = CheckForm(
            f"Enable {self.name}",
            checked=bool(config.get("enabled")),
        )
        layout.addWidget(self.enabled)

        self.path = ControlFilePath(
            str(config.get("executable", "")),
            "Executable files (*.exe);;All files (*)",
        )
        layout.addWidget(FormField("Executable", self.path))

        self.arguments = InputFormText(
            str(config.get("extra_arguments", config.get("arguments", "")) or "")
        )
        self.arguments.setPlaceholderText("Optional solver command-line arguments")
        layout.addWidget(FormField("Additional arguments", self.arguments))

    def values(self) -> dict[str, object]:
        """Return the complete backend configuration represented by this row."""
        return {
            "enabled": self.enabled.isChecked(),
            "executable": self.path.text(),
            "extra_arguments": self.arguments.text().strip(),
        }
