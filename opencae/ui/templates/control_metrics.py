"""Compatibility helpers for shared dialog-control geometry contracts."""

from __future__ import annotations

from PyQt6.QtWidgets import QSizePolicy, QWidget

from opencae.ui.core.metrics import (
    COMBO_POPUP_EXTRA_HEIGHT,
    COMBO_POPUP_ROW_HEIGHT,
    FIELD_LABEL_SPACING,
    INLINE_ACTION_SIZE,
    PRIMARY_CONTROL_HEIGHT,
)


def apply_primary_control_height(widget: QWidget) -> QWidget:
    """Apply the canonical geometry contract for a primary dialog control.

    Qt input classes have different native size hints and stylesheet padding.
    The dynamic property lets QSS normalize their internal vertical padding,
    while the fixed widget height guarantees identical outer geometry.
    """
    widget.setProperty("primaryControl", True)
    widget.setMinimumHeight(PRIMARY_CONTROL_HEIGHT)
    widget.setMaximumHeight(PRIMARY_CONTROL_HEIGHT)
    policy = widget.sizePolicy()
    policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
    widget.setSizePolicy(policy)
    widget.updateGeometry()
    return widget


def apply_inline_action_size(widget: QWidget) -> QWidget:
    """Make an inline action exactly match its neighboring primary field."""
    widget.setProperty("inlineAction", True)
    widget.setFixedSize(INLINE_ACTION_SIZE, INLINE_ACTION_SIZE)
    return widget
