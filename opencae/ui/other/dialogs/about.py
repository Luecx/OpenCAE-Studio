"""Provides the compact application information dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from opencae.ui.primitives.buttons import ButtonFormPrimary
from opencae.ui.primitives.labels import LabelMuted, LabelTitle
from opencae.ui.components.layouts import dialog_layout

class AboutDialog(QDialog):
    """Show product identity and a concise architecture description."""

    def __init__(self, parent=None):
        """Build the informational dialog with the shared dialog spacing."""
        super().__init__(parent)
        self.setWindowTitle("About OpenCAE Studio")
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = dialog_layout(self)
        layout.addWidget(LabelTitle("OpenCAE Studio"))
        description = LabelMuted(
            "Modular PyQt6 CAE modelling prototype\n"
            "Deck-oriented, solver-independent architecture."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        close = ButtonFormPrimary("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
