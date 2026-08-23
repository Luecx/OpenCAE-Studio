"""Defines shared geometry tokens for visually consistent dialog controls."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

PRIMARY_CONTROL_HEIGHT = 40
FIELD_LABEL_SPACING = 6


def apply_primary_control_height(widget: QWidget) -> QWidget:
    """Give a primary dialog control the canonical visual height.

    Qt input classes use different native size hints and stylesheet padding.
    Fixing their final widget height keeps line edits, combo boxes, numeric
    editors, and composed controls visually identical.
    """
    widget.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
    return widget
