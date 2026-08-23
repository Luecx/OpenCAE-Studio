"""Builds canonical label-above-control fields for editor dialogs."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .control_metrics import FIELD_LABEL_SPACING
from .field_label import FieldLabel


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

    # Centralizing the label type keeps typography identical even when fields
    # are assembled by different dialogs or nested editor components.
    layout.addWidget(FieldLabel(label_text))
    layout.addWidget(control)
    return host
