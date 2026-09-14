"""Compact numeric primitive used by matrix/grid editors."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QWidget


class InputMatrixNumber(QDoubleSpinBox):
    """Dense right-aligned numeric cell without spin buttons."""

    def __init__(
        self,
        value: float = 0.0,
        *,
        minimum: float = -1.0e30,
        maximum: float = 1.0e30,
        decimals: int = 8,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MatrixCell")
        self.setRange(float(minimum), float(maximum))
        self.setDecimals(int(decimals))
        self.setValue(float(value))
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setMinimumWidth(76)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
