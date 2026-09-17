"""Reusable label-above-control form field."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.ui.foundation.metrics import FIELD_LABEL_SPACING
from opencae.ui.primitives.labels import LabelForm


class FormField(QWidget):
    """Pair one semantic field caption with one editor control."""

    def __init__(self, label_text: str, control: QWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("PrimaryFieldBlock")
        self.label = LabelForm(str(label_text), self)
        self.control = control

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(FIELD_LABEL_SPACING)
        layout.addWidget(self.label)
        layout.addWidget(self.control)

    def set_label(self, text: str) -> None:
        self.label.setText(str(text))
