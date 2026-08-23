"""Provides a thin reusable separator between editor columns."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame


class VerticalSeparator(QFrame):
    """Draw the shared one-pixel divider used by split editor layouts."""

    def __init__(self, parent=None):
        """Create a vertical separator with no extra content or interaction."""
        super().__init__(parent)
        self.setObjectName("EditorVerticalSeparator")
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
