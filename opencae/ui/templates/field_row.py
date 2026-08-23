"""Builds equal-width horizontal rows from canonical field blocks."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget


def field_row(*fields: QWidget, spacing: int = 16, parent=None) -> QWidget:
    """Return a horizontal row where each labelled field receives equal width."""
    host = QWidget(parent)
    host.setObjectName("PrimaryFieldRow")
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for field in fields:
        layout.addWidget(field, 1)
    return host
