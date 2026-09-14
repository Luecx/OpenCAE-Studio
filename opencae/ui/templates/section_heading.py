"""Provides the canonical heading for grouped editor sections."""

from __future__ import annotations

from opencae.ui.primitives.semantic_label import SemanticLabel


class SectionHeading(SemanticLabel):
    """Render a reusable section title with the shared OpenCAE accent marker."""

    def __init__(self, text: str, parent=None):
        """Create one semantic editor-section heading."""
        super().__init__(
            str(text),
            object_name="EditorSectionHeading",
            parent=parent,
        )
