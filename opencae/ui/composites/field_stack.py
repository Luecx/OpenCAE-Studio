"""Reusable vertical form container built from canonical form fields."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .form_field import FormField


class FieldStack(QWidget):
    """Collect labelled controls vertically with a compact form-like API."""

    def __init__(self, parent=None, *, spacing: int = 12):
        super().__init__(parent)
        self.setObjectName("PrimaryFieldStack")
        self._blocks: dict[QWidget, FormField] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(int(spacing))
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    def addRow(self, label, control: QWidget | None = None) -> QWidget:  # noqa: N802
        if control is None:
            widget = label
            self._layout.addWidget(widget)
            return widget

        label_text = label.text() if hasattr(label, "text") else str(label)
        if not str(label_text).strip():
            self._layout.addWidget(control)
            return control

        block = FormField(str(label_text), control)
        self._blocks[control] = block
        self._layout.addWidget(block)
        return block

    def addWidget(self, widget: QWidget, stretch: int = 0) -> None:  # noqa: N802
        self._layout.addWidget(widget, stretch)

    def labelForField(self, control: QWidget):  # noqa: N802
        block = self._blocks.get(control)
        return block.label if block is not None else None

    def blockForField(self, control: QWidget) -> FormField | None:  # noqa: N802
        return self._blocks.get(control)

    def addStretch(self, stretch: int = 1) -> None:  # noqa: N802
        self._layout.addStretch(stretch)

    def clear(self) -> None:
        self._blocks.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            nested = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif nested is not None:
                while nested.count():
                    child_item = nested.takeAt(0)
                    child = child_item.widget()
                    if child is not None:
                        child.deleteLater()
