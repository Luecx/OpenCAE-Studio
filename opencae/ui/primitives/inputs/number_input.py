"""Canonical floating-point editor."""

from __future__ import annotations

from PyQt6.QtWidgets import QDoubleSpinBox, QWidget

from .geometry import apply_primary_input_geometry


class NumberInput(QDoubleSpinBox):
    """A primary-height floating point input with centralized defaults."""

    def __init__(
        self,
        value: float = 0.0,
        *,
        minimum: float = -1.0e30,
        maximum: float = 1.0e30,
        decimals: int = 8,
        prefix: str = "",
        suffix: str = "",
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setRange(float(minimum), float(maximum))
        self.setDecimals(int(decimals))
        self.setValue(float(value))
        if prefix:
            self.setPrefix(str(prefix))
        if suffix:
            self.setSuffix(str(suffix))
        if object_name:
            self.setObjectName(object_name)
        apply_primary_input_geometry(self)
