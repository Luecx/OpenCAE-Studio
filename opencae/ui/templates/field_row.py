"""Compatibility factory for equal-width horizontal field rows."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from opencae.ui.composites import FieldRow


def field_row(*fields: QWidget, spacing: int = 16, parent=None) -> FieldRow:
    """Return a horizontal row where each labelled field receives equal width."""
    return FieldRow(*fields, spacing=spacing, parent=parent)
