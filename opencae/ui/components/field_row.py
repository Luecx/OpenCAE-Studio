"""Reusable equal-width row of form fields."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget


class FieldRow(QWidget):
    """Lay out related field composites horizontally at equal stretch."""

    def __init__(
        self,
        *fields: QWidget,
        spacing: int = 16,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PrimaryFieldRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(int(spacing))
        for field in fields:
            layout.addWidget(field, 1)
