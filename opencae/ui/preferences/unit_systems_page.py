from copy import deepcopy

from PyQt6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from opencae.model.naming import next_name_from_names, normalized
from opencae.ui.preferences.unit_system_editor import UnitSystemEditor
from opencae.ui.preferences.unit_system_table import UnitSystemTable
from opencae.units import UnitSystem


class UnitSystemsPage(QWidget):
    def __init__(self, systems, selected, parent=None):
        super().__init__(parent); self.systems = [deepcopy(item) for item in systems]; self.selected_name = selected
        root = QHBoxLayout(self); left = QVBoxLayout(); self.list = QListWidget(); left.addWidget(self.list)
        buttons = QHBoxLayout(); self.add = QPushButton("+"); self.copy = QPushButton("Duplicate"); self.remove = QPushButton("−")
        for button in (self.add, self.copy, self.remove): buttons.addWidget(button)
        left.addLayout(buttons); root.addLayout(left, 0)
        right = QVBoxLayout(); note = QLabel("Length, force and time define the mechanical unit system; temperature is the fourth base unit for thermal quantities."); note.setWordWrap(True); note.setObjectName("MutedText"); right.addWidget(note)
        current_form = QFormLayout(); self.current = QComboBox(); current_form.addRow("Current unit system", self.current); right.addLayout(current_form)
        self.editor = UnitSystemEditor(self._editor_changed); right.addWidget(self.editor); self.table = UnitSystemTable(); right.addWidget(self.table, 1); root.addLayout(right, 1)
        self.list.currentRowChanged.connect(self._load); self.current.currentTextChanged.connect(self._current_changed)
        self.add.clicked.connect(self._add); self.copy.clicked.connect(self._duplicate); self.remove.clicked.connect(self._remove); self._refresh(0)

    def _refresh(self, row=None):
        current = self.selected_name; self.list.blockSignals(True); self.list.clear(); self.list.addItems([item.name for item in self.systems]); self.list.blockSignals(False)
        self.current.blockSignals(True); self.current.clear(); self.current.addItems([item.name for item in self.systems]); self.current.setCurrentText(current); self.current.blockSignals(False)
        self.list.setCurrentRow(max(0, min(row if row is not None else self.list.currentRow(), len(self.systems) - 1))); self._load(self.list.currentRow())

    def _load(self, row):
        if row < 0 or not self.systems: return
        self.editor.load(self.systems[row]); self._update_table(); self.remove.setEnabled(len(self.systems) > 1)

    def _editor_changed(self):
        row = self.list.currentRow()
        if row < 0: return
        old = self.systems[row].name; self.editor.apply(self.systems[row])
        if self.selected_name == old: self.selected_name = self.systems[row].name
        self._refresh(row)

    def _current_changed(self, name):
        if name: self.selected_name = name; self._update_table()

    def _update_table(self):
        row = self.list.currentRow()
        if row < 0 or not self.systems: return
        target = next((item for item in self.systems if item.name == self.selected_name), self.systems[0]); self.table.refresh(self.systems[row], target)

    def _add(self):
        name = next_name_from_names("Unit System", [item.name for item in self.systems]); self.systems.append(UnitSystem(name)); self._refresh(len(self.systems) - 1)

    def _duplicate(self):
        row = self.list.currentRow()
        if row < 0: return
        clone = deepcopy(self.systems[row]); clone.name = next_name_from_names(clone.name, [item.name for item in self.systems]); self.systems.append(clone); self._refresh(len(self.systems) - 1)

    def _remove(self):
        row = self.list.currentRow()
        if row < 0 or len(self.systems) <= 1: return
        removed = self.systems.pop(row)
        if removed.name == self.selected_name: self.selected_name = self.systems[0].name
        self._refresh(min(row, len(self.systems) - 1))

    def validate(self):
        names = [item.name.strip() for item in self.systems]
        if any(not name for name in names): return "Every unit system needs a name."
        if len({normalized(name) for name in names}) != len(names): return "Unit-system names must be unique."
        return ""

    def values(self): return self.systems, self.selected_name
