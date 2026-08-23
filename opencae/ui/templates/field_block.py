"""Builds canonical label-above-control fields for editor dialogs."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .control_metrics import FIELD_LABEL_SPACING


def field_block(label_text: str, control: QWidget, parent=None) -> QWidget:
    """Return one editor field with its label directly above the control.

    Editor dialogs deliberately use a vertical label hierarchy so unrelated Qt
    widget classes can be combined without introducing independent form columns.
    """
    host = QWidget(parent)
    host.setObjectName("PrimaryFieldBlock")

    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(FIELD_LABEL_SPACING)

    label = QLabel(label_text)
    label.setObjectName("PrimaryFieldLabel")
    layout.addWidget(label)
    layout.addWidget(control)
    return host
