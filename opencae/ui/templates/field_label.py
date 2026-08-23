"""Provides the canonical label used above editor controls and values."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel


class FieldLabel(QLabel):
    """Render the shared muted label used by label-above-control fields."""

    def __init__(self, text: str, parent=None):
        """Create one semantic editor-field label."""
        super().__init__(str(text), parent)
        self.setObjectName("PrimaryFieldLabel")
