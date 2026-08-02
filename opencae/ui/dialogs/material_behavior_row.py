from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton


class MaterialBehaviorRow(QFrame):
    add_requested = pyqtSignal(str)
    remove_requested = pyqtSignal(str)

    def __init__(self, category, parent=None):
        super().__init__(parent); self.category = category; self.setObjectName("MaterialBehaviorRow")
        layout = QHBoxLayout(self); layout.setContentsMargins(10, 7, 8, 7); layout.setSpacing(8)
        title = QLabel(category); title.setMinimumWidth(150); title.setObjectName("BehaviorCategory"); layout.addWidget(title)
        self.value = QLabel("Not defined"); self.value.setObjectName("BehaviorValue"); layout.addWidget(self.value, 1)
        add = QToolButton(); add.setText("+"); add.setToolTip(f"Add or edit {category}")
        remove = QToolButton(); remove.setText("−"); remove.setToolTip(f"Remove {category}")
        add.clicked.connect(lambda: self.add_requested.emit(category)); remove.clicked.connect(lambda: self.remove_requested.emit(category))
        layout.addWidget(add); layout.addWidget(remove)

    def set_behavior(self, behavior):
        self.value.setText(behavior.behavior_type if behavior else "Not defined")
        self.setProperty("defined", behavior is not None)
        self.style().unpolish(self); self.style().polish(self)
