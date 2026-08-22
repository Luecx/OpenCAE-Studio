from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QLabel, QWidget

from opencae.ui.core.unit_context import unit_system_for


class ComponentsWidget(QWidget):
    def __init__(self, labels, values=None, checkable=False, editable=True, parent=None, quantities=None):
        super().__init__(parent)
        self._checks = []
        self._values = []
        current = list(values or [None] * len(labels))
        if quantities is None:
            quantities = [None] * len(labels)
        elif isinstance(quantities, str):
            quantities = [quantities] * len(labels)
        else:
            quantities = list(quantities)
        unit_system = unit_system_for(self)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(5)
        for row, (label, quantity) in enumerate(zip(labels, quantities)):
            check = QCheckBox(label) if checkable else None
            text = check if check else QLabel(label)
            value = QDoubleSpinBox()
            value.setDecimals(12)
            value.setRange(-1.0e300, 1.0e300)
            value.setValue(float(current[row] or 0.0))
            if quantity:
                value.setSuffix(f" {unit_system.symbol(quantity)}")
            value.setEnabled(editable and (not checkable or current[row] is not None))
            if check:
                check.setChecked(current[row] is not None)
                check.toggled.connect(value.setEnabled if editable else lambda _state: None)
            layout.addWidget(text, row, 0)
            layout.addWidget(value, row, 1)
            self._checks.append(check)
            self._values.append(value)

    def values(self):
        return [widget.value() if check is None or check.isChecked() else None for check, widget in zip(self._checks, self._values)]

    def set_values(self, values):
        for check, widget, value in zip(self._checks, self._values, values):
            if check is not None:
                check.setChecked(value is not None)
            widget.setValue(float(value or 0.0))
