"""Application-scale appearance preferences independent of color schemes."""

from __future__ import annotations

from opencae.ui.templates import FieldLabel

from .page import PreferencePage


class AppearancePage(PreferencePage):
    """Edit interface scaling while color schemes remain owned by the View menu."""

    def __init__(self, settings, parent=None):
        super().__init__(
            "Appearance",
            "Adjust interface scale without duplicating the global color-scheme selector.",
            parent,
        )
        self.add_section("Interface")
        self.add_field(
            settings,
            "appearance/font_scale",
            "Font scale",
            default=100,
            kind="int",
            minimum=80,
            maximum=140,
            suffix=" %",
        )
        note = FieldLabel(
            "Color scheme remains under View → Color Scheme so there is exactly one authoritative theme selector."
        )
        note.setWordWrap(True)
        self.root.addWidget(note)
        self.finish()
