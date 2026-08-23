"""Provides a vertical form container built from canonical label-above fields."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .field_block import FieldBlock, field_block


class FieldStack(QWidget):
    """Collect labelled controls vertically while preserving a small form-like API."""

    def __init__(self, parent=None, *, spacing: int = 12):
        """Create an empty field stack with dialog-consistent spacing."""
        super().__init__(parent)
        self.setObjectName("PrimaryFieldStack")
        self._blocks: dict[QWidget, FieldBlock] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)

    def addRow(self, label, control: QWidget | None = None) -> QWidget:
        """Append a labelled control or one standalone widget.

        The method intentionally mirrors the small subset of QFormLayout used by
        legacy OpenCAE dialog shells. New code can therefore migrate to the
        label-above hierarchy without every subclass needing a bespoke rewrite.
        """
        if control is None:
            widget = label
            self._layout.addWidget(widget)
            return widget

        label_text = label.text() if hasattr(label, "text") else str(label)
        if not str(label_text).strip():
            # Checkboxes and descriptive rows already carry their own caption;
            # adding an empty FieldLabel would create unexplained vertical air.
            self._layout.addWidget(control)
            return control

        block = field_block(str(label_text), control)
        self._blocks[control] = block
        self._layout.addWidget(block)
        return block

    def addWidget(self, widget: QWidget, stretch: int = 0) -> None:
        """Append an unlabelled widget to the field stack."""
        self._layout.addWidget(widget, stretch)

    def labelForField(self, control: QWidget):
        """Return the semantic label associated with a previously added control."""
        block = self._blocks.get(control)
        return block.label if block is not None else None

    def blockForField(self, control: QWidget) -> FieldBlock | None:
        """Return the complete labelled block associated with one control."""
        return self._blocks.get(control)

    def addStretch(self, stretch: int = 1) -> None:
        """Append flexible vertical space below the current fields."""
        self._layout.addStretch(stretch)
