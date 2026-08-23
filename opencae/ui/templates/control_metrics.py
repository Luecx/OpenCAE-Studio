"""Defines shared geometry tokens for visually consistent dialog controls."""

from __future__ import annotations

from PyQt6.QtWidgets import QSizePolicy, QWidget

PRIMARY_CONTROL_HEIGHT = 40
INLINE_ACTION_SIZE = PRIMARY_CONTROL_HEIGHT
COMBO_POPUP_ROW_HEIGHT = 36
COMBO_POPUP_EXTRA_HEIGHT = 8
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
    """Make an inline create/pick action exactly match its neighboring field.

    Inline actions share the 40 px outer box of primary controls.  Their visual
    weight remains secondary through icon/glyph styling rather than a smaller
    geometry, which keeps composite rows perfectly aligned without clipping.
    """
    widget.setProperty("inlineAction", True)
    widget.setFixedSize(INLINE_ACTION_SIZE, INLINE_ACTION_SIZE)
    return widget
