from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget

class PickReference(QWidget):
    pick_requested = pyqtSignal(object, object)
    changed = pyqtSignal()

    def __init__(self, allowed, parent=None):
        super().__init__(parent); self.allowed = tuple(allowed); self._reference = None
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(5)
        self.text = QLineEdit(); self.text.setReadOnly(True); self.text.setPlaceholderText("Not selected")
        self.pick = QPushButton("Pick"); self.pick.setObjectName("ContextPickButton"); self.pick.setCheckable(True)
        clear = QPushButton("×"); clear.setFixedWidth(30)
        self.pick.clicked.connect(self._pick); clear.clicked.connect(lambda: self.set_reference(None))
        layout.addWidget(self.text, 1); layout.addWidget(self.pick); layout.addWidget(clear)

    def set_reference(self, reference):
        self.pick.setChecked(False)
        self._reference = dict(reference) if reference else None
        self.text.setText(self._reference.get("name", "") if self._reference else ""); self.changed.emit()

    def reference(self): return dict(self._reference) if self._reference else None

    def _pick(self):
        self.pick.setChecked(True)
        self.pick_requested.emit(self.allowed, self.set_reference)
