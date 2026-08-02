from PyQt6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLineEdit

from opencae.units.catalog import BASE_CATALOGS


class UnitSystemEditor(QGroupBox):
    def __init__(self, changed, parent=None):
        super().__init__("Base units", parent); form = QFormLayout(self); self.changed = changed
        self.name = QLineEdit(); form.addRow("Name", self.name)
        self.combos = {}
        for key, label in (("length", "Length"), ("force", "Force"), ("time", "Time"), ("temperature", "Temperature")):
            combo = QComboBox(); combo.addItems(tuple(BASE_CATALOGS[key])); self.combos[key] = combo; form.addRow(label, combo)
        self.name.editingFinished.connect(changed)
        for combo in self.combos.values(): combo.currentTextChanged.connect(lambda _text, callback=changed: callback())

    def load(self, system):
        self.name.blockSignals(True); self.name.setText(system.name); self.name.blockSignals(False)
        for key, combo in self.combos.items():
            combo.blockSignals(True); combo.setCurrentText(getattr(system, key)); combo.blockSignals(False)

    def apply(self, system):
        system.name = self.name.text().strip()
        for key, combo in self.combos.items(): setattr(system, key, combo.currentText())
