from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
class PythonConsole(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); label=QLabel('Embedded Python console is reserved for a later milestone.'); label.setWordWrap(True); layout.addWidget(label); layout.addStretch(1)
