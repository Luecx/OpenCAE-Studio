"""Default geometry-import preferences for newly created Parts."""

from __future__ import annotations

from .page import PreferencePage


class GeometryPage(PreferencePage):
    """Edit geometry defaults copied into new Parts without changing existing models."""

    def __init__(self, settings, parent=None):
        super().__init__(
            "Geometry",
            "These values initialize new Parts and new CAD imports. Existing Part settings are never overwritten.",
            parent,
        )
        self.add_section("Import & healing")
        self.add_toggle(settings, "geometry/heal_on_import", "Heal imported geometry", default=True)
        self.add_toggle(settings, "geometry/sew_faces", "Sew adjacent faces", default=True)
        self.add_toggle(settings, "geometry/make_solids", "Create solids from closed shells", default=True)
        self.add_toggle(settings, "geometry/remove_degenerate", "Remove degenerate entities", default=True)
        self.add_field(
            settings,
            "geometry/tolerance",
            "Import tolerance",
            default=1.0e-7,
            kind="float",
            minimum=1.0e-12,
            maximum=1.0,
            decimals=10,
        )
        self.add_section("Display")
        self.add_field(
            settings,
            "geometry/display_size_factor",
            "Datum / reference display size factor",
            default=0.025,
            kind="float",
            minimum=0.001,
            maximum=0.25,
            decimals=4,
        )
        self.finish()
