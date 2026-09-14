"""Canonical integer input used in forms and inspectors."""

from __future__ import annotations

from PyQt6.QtWidgets import QSpinBox, QWidget

from .geometry import apply_primary_input_geometry


class InputFormInteger(QSpinBox):
    def __init__(
        self,
        value: int = 0,
        *,
        minimum: int = -2_147_483_648,
        maximum: int = 2_147_483_647,
        suffix: str = "",
        prefix: str = "",
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setRange(int(minimum), int(maximum))
        if suffix:
            self.setSuffix(str(suffix))
        if prefix:
            self.setPrefix(str(prefix))
        if object_name:
            self.setObjectName(object_name)
        self.setValue(int(value))
        apply_primary_input_geometry(self)
