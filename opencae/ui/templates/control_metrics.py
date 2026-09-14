"""Compatibility helpers for shared dialog-control geometry contracts."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from opencae.ui.core.metrics import (
    COMBO_POPUP_EXTRA_HEIGHT,
    COMBO_POPUP_ROW_HEIGHT,
    FIELD_LABEL_SPACING,
    INLINE_ACTION_SIZE,
    PRIMARY_CONTROL_HEIGHT,
)
from opencae.ui.primitives.inputs.geometry import apply_primary_input_geometry


def apply_primary_control_height(widget: QWidget) -> QWidget:
    """Backward-compatible alias for the canonical primary-input geometry."""
    return apply_primary_input_geometry(widget)


def apply_inline_action_size(widget: QWidget) -> QWidget:
    """Make an inline action exactly match its neighboring primary field."""
    widget.setProperty("inlineAction", True)
    widget.setFixedSize(INLINE_ACTION_SIZE, INLINE_ACTION_SIZE)
    return widget
