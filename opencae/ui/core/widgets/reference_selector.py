from __future__ import annotations

from collections.abc import Callable, Iterable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from .chevron_combo import ChevronComboBox
from opencae.ui.core.dialog_lifecycle import activate_dialog


class ReferenceSelector(QWidget):
    value_changed = pyqtSignal(object)

    def __init__(self, values: Iterable = (), current=None, create_callback: Callable | None = None, pick_callback: Callable | None = None, parent=None):
        super().__init__(parent)
        self.combo = ChevronComboBox(); self.combo.setObjectName("ReferenceCombo"); self.combo.setMinimumWidth(0)
        self._add_values(values); self.setCurrentValue(current)
        self.combo.currentIndexChanged.connect(lambda _index: self.value_changed.emit(self.currentValue()))
        self.add_button = QPushButton("+"); self.add_button.setObjectName("InlineAddButton"); self.add_button.setToolTip("Create a new referenced object"); self.add_button.setFixedSize(30, 30)
        self._create_callback = create_callback; self.add_button.setVisible(create_callback is not None); self.add_button.clicked.connect(self._create)
        self.pick_button = QPushButton("⌖"); self.pick_button.setObjectName("InlinePickButton"); self.pick_button.setCheckable(True); self.pick_button.setToolTip("Pick the referenced object in the viewport"); self.pick_button.setFixedSize(30,30)
        self._pick_callback = pick_callback; self.pick_button.setVisible(pick_callback is not None); self.pick_button.clicked.connect(self._pick)
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(6); layout.addWidget(self.combo, 1); layout.addWidget(self.pick_button); layout.addWidget(self.add_button)
        self.setMinimumWidth(316)

    @staticmethod
    def _option(value):
        if hasattr(value, "id") and hasattr(value, "name"): return str(value.name), str(value.id)
        if isinstance(value, tuple) and len(value) == 2: return str(value[0]), value[1]
        return str(value), value

    def _add_values(self, values):
        for value in values:
            label, data = self._option(value); self.combo.addItem(label, data)

    def currentText(self): return self.combo.currentText()
    def currentData(self): return self.combo.currentData()
    def currentValue(self): return self.currentData()
    def current_id(self): return self.currentData()

    def setCurrentText(self, value): self.combo.setCurrentText(str(value or ""))

    def setCurrentValue(self, value):
        if value is None or value == "": return
        if hasattr(value, "id"): value = value.id
        index = self.combo.findData(value)
        if index < 0: index = self.combo.findText(str(value))
        if index >= 0: self.combo.setCurrentIndex(index)

    def clear(self):
        self.combo.setCurrentIndex(-1)
        self.value_changed.emit(self.currentValue())

    def set_values(self, values, current=None):
        previous = self.currentValue() if current in (None, "") else current
        self.combo.blockSignals(True); self.combo.clear(); self._add_values(values); self.setCurrentValue(previous); self.combo.blockSignals(False)

    def _apply_created(self, value):
        self.pick_button.setChecked(False)
        if not value: return
        label, data = self._option(value)
        index = self.combo.findData(data)
        if index < 0: self.combo.addItem(label, data); index = self.combo.count() - 1
        self.combo.setCurrentIndex(index); activate_dialog(self)

    def _create(self):
        callback = self._create_callback
        if callback is None: return
        callback(self.window(), self._apply_created)

    def _pick(self):
        callback = self._pick_callback
        if callback is None: return
        self.pick_button.setChecked(True)
        callback(self.window(), self._apply_created)
