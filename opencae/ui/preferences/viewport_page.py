"""3D viewport presentation preferences."""

from __future__ import annotations

from .page import PreferencePage


class ViewportPage(PreferencePage):
    """Edit persistent camera, orientation and framing defaults."""

    def __init__(self, settings, parent=None):
        super().__init__(
            "Viewport",
            "Choose persistent camera defaults and orientation controls shown around the model.",
            parent,
        )
        self.add_section("Camera")
        self.add_field(
            settings,
            "viewport/projection",
            "Projection",
            default="Perspective",
            kind="choice",
            choices=("Perspective", "Parallel"),
        )
        self.add_toggle(
            settings,
            "viewport/auto_fit_loaded_content",
            "Automatically fit newly opened projects, CAD and imported meshes",
            default=True,
        )

        self.add_section("Orientation")
        self.add_toggle(
            settings,
            "viewport/show_view_cube",
            "Show the ViewCube",
            default=True,
        )
        self.finish()
