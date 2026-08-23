"""Compatibility name for the canonical numeric unit input used by Materials."""

from __future__ import annotations

from opencae.ui.templates import NumericUnitInput


class MaterialPropertyInput(NumericUnitInput):
    """Preserve the Material-dialog type name while using shared control metrics."""

    def __init__(self, value: float, unit: str = "", parent=None):
        super().__init__(value=value, unit=unit, parent=parent)
