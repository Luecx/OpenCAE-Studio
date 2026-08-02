from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class SolverRow(QWidget):
    def __init__(self, name, config, parent=None):
        super().__init__(parent)
        self.name = name
        self.enabled = QCheckBox()
        self.enabled.setChecked(bool(config.get("enabled")))
        self.label = QLabel(name); self.label.setMinimumWidth(85)
        self.path = QLineEdit(str(config.get("executable", "")))
        self.path.setPlaceholderText("Executable path")
        self.browse = QPushButton("Browse…")
        self.browse.clicked.connect(self._browse)
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(8)
        layout.addWidget(self.enabled); layout.addWidget(self.label); layout.addWidget(self.path, 1); layout.addWidget(self.browse)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, f"Select {self.name} executable")
        if path: self.path.setText(path)

    def values(self):
        return {"enabled": self.enabled.isChecked(), "executable": self.path.text().strip(), "extra_arguments": ""}
