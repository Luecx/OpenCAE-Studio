"""Default post-processing presentation preferences."""

from __future__ import annotations

from .page import PreferencePage


class ResultsPage(PreferencePage):
    """Edit visual defaults applied to result inspection controls."""

    def __init__(self, settings, parent=None):
        super().__init__(
            "Results",
            "Choose the default visual overlays used when inspecting solver results.",
            parent,
        )
        self.add_section("Result display")
        self.add_toggle(
            settings,
            "results/show_mesh_lines",
            "Show mesh lines",
            default=True,
        )
        self.add_toggle(
            settings,
            "results/show_boundary_lines",
            "Show model boundaries",
            default=True,
        )
        self.add_toggle(
            settings,
            "results/show_undeformed",
            "Show undeformed reference shape",
            default=False,
        )
        self.finish()
