"""Canonical floating-point input used in forms and inspectors."""

from __future__ import annotations

from PyQt6.QtWidgets import QDoubleSpinBox, QWidget

from .geometry import apply_primary_input_geometry


class InputFormNumber(QDoubleSpinBox):
    def __init__(
        self,
        value: float = 0.0,
        *,
        minimum: float = -1.0e30,
        maximum: float = 1.0e30,
        decimals: int = 8,
        step: float | None = None,
        suffix: str = "",
        prefix: str = "",
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setRange(float(minimum), float(maximum))
        self.setDecimals(int(decimals))
        if step is not None:
            self.setSingleStep(float(step))
        if suffix:
            self.setSuffix(str(suffix))
        if prefix:
            self.setPrefix(str(prefix))
        if object_name:
            self.setObjectName(object_name)
        self.setValue(float(value))
        apply_primary_input_geometry(self)
