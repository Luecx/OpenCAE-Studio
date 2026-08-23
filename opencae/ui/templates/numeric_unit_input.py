"""Provides the canonical numeric input with an optional fixed unit segment."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QWidget

from .control_metrics import apply_primary_control_height


class NumericUnitInput(QWidget):
    """Edit a scalar value while rendering its unit as a non-editable right cell."""

    valueChanged = pyqtSignal(float)

    def __init__(
        self,
        value: float = 0.0,
        unit: str = "",
        *,
        minimum: float = -1e30,
        maximum: float = 1e30,
        decimals: int = 8,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("NumericUnitInput")
        apply_primary_control_height(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.editor = QDoubleSpinBox()
        self.editor.setObjectName("PrimaryNumericWithUnit" if unit else "PrimaryNumeric")
        self.editor.setMinimumWidth(0)
        self.editor.setRange(minimum, maximum)
        self.editor.setDecimals(decimals)
        self.editor.setValue(float(value))
        apply_primary_control_height(self.editor)
        self.editor.valueChanged.connect(self.valueChanged.emit)
        layout.addWidget(self.editor, 1)

        self.unit_label = None
        if unit:
            # The unit is display metadata. Keeping it out of the editor makes
            # number alignment stable and prevents it from behaving like input.
            self.unit_label = QLabel(unit)
            self.unit_label.setObjectName("PrimaryUnitLabel")
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            apply_primary_control_height(self.unit_label)
            layout.addWidget(self.unit_label)

    def value(self) -> float:
        """Return the current scalar value."""
        return self.editor.value()

    def setValue(self, value: float) -> None:
        """Replace the current scalar value."""
        self.editor.setValue(float(value))

    def setRange(self, minimum: float, maximum: float) -> None:
        """Replace the accepted numeric range."""
        self.editor.setRange(minimum, maximum)

    def setDecimals(self, decimals: int) -> None:
        """Replace the number of displayed decimal places."""
        self.editor.setDecimals(decimals)
