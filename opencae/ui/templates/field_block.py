"""Provides the canonical label-above-control block used by editor dialogs."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .control_metrics import FIELD_LABEL_SPACING
from .field_label import FieldLabel


class FieldBlock(QWidget):
    """Pair one semantic field label with one control in a reusable vertical block."""

    def __init__(self, label_text: str, control: QWidget, parent=None):
        """Build a field whose label can later be changed without rebuilding layout."""
        super().__init__(parent)
        self.setObjectName("PrimaryFieldBlock")
        self.label = FieldLabel(label_text)
        self.control = control

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(FIELD_LABEL_SPACING)
        layout.addWidget(self.label)
        layout.addWidget(self.control)

    def set_label(self, text: str) -> None:
        """Replace the visible field caption while preserving the control geometry."""
        self.label.setText(str(text))


def field_block(label_text: str, control: QWidget, parent=None) -> FieldBlock:
    """Return the canonical reusable field block for one dialog control."""
    return FieldBlock(label_text, control, parent)
