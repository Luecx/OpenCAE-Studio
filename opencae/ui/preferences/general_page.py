"""General application behavior preferences."""

from __future__ import annotations

from .page import PreferencePage


class GeneralPage(PreferencePage):
    """Edit deletion confirmation and workspace restoration behavior."""

    def __init__(self, settings, parent=None):
        super().__init__(
            "General",
            "Configure application-wide behavior. Project-owned values remain in Project Properties.",
            parent,
        )
        self.add_section("Behavior")
        self.add_toggle(
            settings,
            "ui/confirm_delete",
            "Confirm direct model-object deletion",
            default=True,
        )
        self.add_toggle(
            settings,
            "ui/restore_layout",
            "Restore dock and workspace layout when OpenCAE starts",
            default=True,
        )
        self.finish()
