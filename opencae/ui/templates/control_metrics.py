"""Defines shared geometry tokens for visually consistent dialog controls."""

from __future__ import annotations

from PyQt6.QtWidgets import QSizePolicy, QWidget

PRIMARY_CONTROL_HEIGHT = 40
INLINE_ACTION_SIZE = 32
FIELD_LABEL_SPACING = 6


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
    """Size a secondary create/pick action without competing with its field."""
    widget.setProperty("inlineAction", True)
    widget.setFixedSize(INLINE_ACTION_SIZE, INLINE_ACTION_SIZE)
    return widget
