"""Default Gmsh preferences for newly created Parts."""

from __future__ import annotations

from .page import PreferencePage


class MeshingPage(PreferencePage):
    """Edit mesher defaults copied into new Part mesh states."""

    def __init__(self, settings, parent=None):
        super().__init__(
            "Meshing",
            "Configure default Gmsh algorithms and optimization. Existing Part mesh settings remain project-owned.",
            parent,
        )
        self.add_section("Algorithms")
        self.add_field(
            settings,
            "mesh/algorithm_2d",
            "2D algorithm",
            default="Frontal-Delaunay",
            kind="choice",
            choices=("MeshAdapt", "Automatic", "Delaunay", "Frontal-Delaunay", "BAMG"),
        )
        self.add_field(
            settings,
            "mesh/algorithm_3d",
            "3D algorithm",
            default="HXT",
            kind="choice",
            choices=("Delaunay", "Frontal", "MMG3D", "R-tree", "HXT"),
        )
        self.add_field(
            settings,
            "mesh/element_order",
            "Element order",
            default=1,
            kind="choice",
            choices=("1", "2"),
        )
        self.add_section("Optimization")
        self.add_toggle(settings, "mesh/optimize", "Optimize generated mesh", default=True)
        self.add_toggle(settings, "mesh/high_order_optimize", "Optimize high-order elements", default=True)
        self.add_toggle(
            settings,
            "mesh/recombine_all",
            "Recombine eligible triangles / tetrahedral surfaces where supported",
            default=False,
        )
        self.add_section("Performance")
        self.add_field(
            settings,
            "mesh/num_threads",
            "Meshing threads (0 = automatic)",
            default=0,
            kind="int",
            minimum=0,
            maximum=256,
        )
        self.finish()

    def values(self):
        values = super().values()
        values["mesh/element_order"] = int(values["mesh/element_order"])
        return values
