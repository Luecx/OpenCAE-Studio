"""Canonical integer editor."""

from __future__ import annotations

from PyQt6.QtWidgets import QSpinBox, QWidget

from .geometry import apply_primary_input_geometry


class IntegerInput(QSpinBox):
    """A primary-height integer input with explicit range and value."""

    def __init__(
        self,
        value: int = 0,
        *,
        minimum: int = -2_147_483_648,
        maximum: int = 2_147_483_647,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setRange(int(minimum), int(maximum))
        self.setValue(int(value))
        if object_name:
            self.setObjectName(object_name)
        apply_primary_input_geometry(self)
