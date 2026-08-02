from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout

from opencae.ui.core.controls import primary_button


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About OpenCAE Studio")
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        title = QLabel("OpenCAE Studio")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)
        description = QLabel(
            "Modular PyQt6 CAE modelling prototype\n"
            "Deck-oriented, solver-independent architecture."
        )
        description.setObjectName("MutedLabel")
        description.setWordWrap(True)
        layout.addWidget(description)
        close = primary_button("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
