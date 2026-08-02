from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from .chevron_combo import ChevronComboBox


class ReferenceSelector(QWidget):
    value_changed = pyqtSignal(str)

    def __init__(self, values: Iterable[str] = (), current: str = "", create_callback: Callable | None = None, parent=None):
        super().__init__(parent)
        self.combo = ChevronComboBox(); self.combo.setObjectName("ReferenceCombo"); self.combo.setMinimumWidth(0); self.combo.addItems(tuple(values))
        if current: self.combo.setCurrentText(current)
        self.combo.currentTextChanged.connect(self.value_changed.emit)
        self.add_button = QPushButton("+"); self.add_button.setObjectName("InlineAddButton"); self.add_button.setToolTip("Create a new referenced object"); self.add_button.setFixedSize(30, 30)
        self._create_callback = create_callback; self.add_button.setVisible(create_callback is not None); self.add_button.clicked.connect(self._create)
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(6); layout.addWidget(self.combo, 1); layout.addWidget(self.add_button)
        self.setMinimumWidth(316)

    def currentText(self): return self.combo.currentText()
    def setCurrentText(self, value): self.combo.setCurrentText(value)

    def set_values(self, values, current=""):
        previous = current or self.currentText(); self.combo.blockSignals(True); self.combo.clear(); self.combo.addItems(tuple(values))
        if previous: self.combo.setCurrentText(previous)
        self.combo.blockSignals(False)

    def _apply_created(self, value):
        if not value: return
        if self.combo.findText(value) < 0: self.combo.addItem(value)
        self.combo.setCurrentText(value); self.window().raise_(); self.window().activateWindow()

    def _create(self):
        callback = self._create_callback
        if callback is None: return
        parameters = len(inspect.signature(callback).parameters)
        if parameters >= 2:
            callback(self.window(), self._apply_created); return
        value = callback(self.window()) if parameters == 1 else callback()
        self._apply_created(value)
