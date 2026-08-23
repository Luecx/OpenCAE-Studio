"""Provides a read-only value field with an optional fixed unit segment."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from .control_metrics import apply_primary_control_height


class ReadOnlyValue(QWidget):
    """Display a derived scalar using the same geometry as editable controls."""

    def __init__(self, value: str = "", unit: str = "", parent=None):
        """Create a non-focusable value field with an optional unit cell."""
        super().__init__(parent)
        self.setObjectName("ReadOnlyValue")
        apply_primary_control_height(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName(
            "ReadOnlyValueTextWithUnit" if unit else "ReadOnlyValueText"
        )
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        apply_primary_control_height(self.value_label)
        layout.addWidget(self.value_label, 1)

        self.unit_label = None
        if unit:
            self.unit_label = QLabel(str(unit))
            self.unit_label.setObjectName("ReadOnlyValueUnit")
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            apply_primary_control_height(self.unit_label)
            layout.addWidget(self.unit_label)

    def set_value(self, value: str, unit: str | None = None) -> None:
        """Update the displayed value and, when supplied, its unit text."""
        self.value_label.setText(str(value))
        if unit is not None and self.unit_label is not None:
            self.unit_label.setText(str(unit))
