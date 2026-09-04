"""General application behavior preferences."""

from __future__ import annotations

from .page import PreferencePage


class GeneralPage(PreferencePage):
    """Edit confirmation, layout restoration and legacy icon sizing preferences."""

    def __init__(self, settings, parent=None):
        super().__init__(
            "General",
            "Configure application-wide behavior. Project-owned values remain in Project Properties.",
            parent,
        )
        self.add_section("Interface")
        self.add_field(
            settings,
            "ui/icon_scale",
            "Icon scale",
            default="Normal",
            kind="choice",
            choices=("Compact", "Normal", "Large"),
        )
        self.add_section("Behavior")
        self.add_toggle(
            settings,
            "ui/confirm_delete",
            "Confirm destructive actions before deleting model data",
            default=True,
        )
        self.add_toggle(
            settings,
            "ui/restore_layout",
            "Restore dock and workspace layout when OpenCAE starts",
            default=True,
        )
        self.finish()
