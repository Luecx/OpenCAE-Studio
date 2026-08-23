"""Provides the numeric material-property editor with an optional unit segment."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QWidget


class MaterialPropertyInput(QWidget):
    """Edit one numeric material value and display its unit as a fixed suffix cell."""

    def __init__(self, value: float, unit: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("MaterialPropertyInput")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.editor = QDoubleSpinBox()
        self.editor.setObjectName(
            "MaterialPropertySpinWithUnit" if unit else "MaterialPropertySpin"
        )
        self.editor.setRange(-1e30, 1e30)
        self.editor.setDecimals(8)
        self.editor.setValue(float(value))
        layout.addWidget(self.editor, 1)

        self.unit_label = None
        if unit:
            # Units are presentation metadata, not another editable model value.
            self.unit_label = QLabel(unit)
            self.unit_label.setObjectName("MaterialPropertyUnit")
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.unit_label)

    def value(self) -> float:
        """Return the current numeric value in project display units."""
        return self.editor.value()

    def setValue(self, value: float) -> None:
        """Replace the displayed numeric value."""
        self.editor.setValue(float(value))
