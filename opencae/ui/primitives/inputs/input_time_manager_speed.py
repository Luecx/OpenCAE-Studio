"""Compact playback-speed number input used by the result Time Manager."""

from PyQt6.QtWidgets import QDoubleSpinBox, QWidget


class InputTimeManagerSpeed(QDoubleSpinBox):
    def __init__(self, value: float = 1.0, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setRange(0.25, 4.0)
        self.setSingleStep(0.25)
        self.setDecimals(2)
        self.setValue(float(value))
        self.setSuffix(" x")
        self.setFixedWidth(76)
