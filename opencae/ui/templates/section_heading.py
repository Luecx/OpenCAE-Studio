"""Provides the canonical heading for grouped editor sections."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel


class SectionHeading(QLabel):
    """Render a reusable section title with the shared OpenCAE accent marker."""

    def __init__(self, text: str, parent=None):
        """Create one semantic editor-section heading."""
        super().__init__(str(text), parent)
        self.setObjectName("EditorSectionHeading")
