from os import cpu_count
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox, QVBoxLayout


class JobSettingsDialog(QDialog):
    def __init__(self, solver, extra_arguments="", parent=None):
        super().__init__(parent); self.solver = solver; self.setWindowTitle(f"Run with {solver}"); self.setMinimumWidth(480)
        root = QVBoxLayout(self); form = QFormLayout(); self.threads = QSpinBox(); self.threads.setRange(1, max(1, cpu_count() or 1)); self.threads.setValue(1)
        self.extra = QLineEdit(extra_arguments)
        if solver == "FEMaster": form.addRow("CPU threads", self.threads)
        form.addRow("Additional arguments", self.extra); root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def values(self): return {"threads": self.threads.value(), "extra_arguments": self.extra.text().strip()}
