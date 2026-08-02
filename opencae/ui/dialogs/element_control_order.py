from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from opencae.model.element_catalog import formulations, resulting_type
from opencae.model.entities.mesh import ElementOrder


class ElementOrderPanel(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent); root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(7)
        row = QHBoxLayout(); self.first = QCheckBox("First Order"); self.second = QCheckBox("Second Order")
        for button in (self.first, self.second): button.setTristate(True); row.addWidget(button)
        row.addStretch(1); root.addLayout(row); self.mixed = QLabel(); self.mixed.setObjectName("FieldHint"); root.addWidget(self.mixed)
        form = QFormLayout(); self.formulation = QComboBox(); self.result = QLabel("—")
        form.addRow("Formulation", self.formulation); form.addRow("Resulting type", self.result); root.addLayout(form)
        self.first.clicked.connect(lambda: self._choose(ElementOrder.FIRST)); self.second.clicked.connect(lambda: self._choose(ElementOrder.SECOND))
        self.formulation.currentTextChanged.connect(self._update_result); self.key = None

    def set_summary(self, summary):
        self.key = summary.key if summary else None
        if not summary:
            self.first.setCheckState(Qt.CheckState.Unchecked); self.second.setCheckState(Qt.CheckState.Unchecked)
            self.mixed.clear(); self.formulation.blockSignals(True); self.formulation.clear(); self.formulation.blockSignals(False)
            self.result.setText("—"); return
        mixed = bool(summary.first and summary.second); self.first.setCheckState(Qt.CheckState.PartiallyChecked if mixed else Qt.CheckState.Checked if summary.first else Qt.CheckState.Unchecked)
        self.second.setCheckState(Qt.CheckState.PartiallyChecked if mixed else Qt.CheckState.Checked if summary.second else Qt.CheckState.Unchecked)
        self.mixed.setText(f"Mixed order: {summary.first:,} first-order / {summary.second:,} second-order" if mixed else "")
        self.formulation.blockSignals(True); self.formulation.clear(); self.formulation.addItem("Keep Existing")
        choices = formulations(summary.key); self.formulation.addItems(choices)
        current = next(iter(summary.formulations)) if len(summary.formulations) == 1 else "Keep Existing"
        self.formulation.setCurrentText(current if current in choices else "Keep Existing")
        self.formulation.blockSignals(False); self._update_result()

    def choose(self, order): self._choose(ElementOrder(order))

    def set_formulation(self, value):
        index = self.formulation.findText(str(value))
        if index >= 0: self.formulation.setCurrentIndex(index)

    def _choose(self, order):
        self.first.setCheckState(Qt.CheckState.Checked if order == ElementOrder.FIRST else Qt.CheckState.Unchecked)
        self.second.setCheckState(Qt.CheckState.Checked if order == ElementOrder.SECOND else Qt.CheckState.Unchecked); self.mixed.clear(); self._update_result(); self.changed.emit()

    def order(self):
        if self.first.checkState() == Qt.CheckState.Checked: return ElementOrder.FIRST
        if self.second.checkState() == Qt.CheckState.Checked: return ElementOrder.SECOND
        return None

    def _update_result(self, *_):
        form = self.formulation.currentText()
        self.result.setText("Preserve current formulations" if not self.key or form == "Keep Existing" or not self.order() else resulting_type(self.key, self.order(), form)); self.changed.emit()
