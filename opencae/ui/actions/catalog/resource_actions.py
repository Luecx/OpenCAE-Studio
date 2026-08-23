"""Registers material, field, section, and profile resource actions."""

from opencae.controllers.material_browser import add_material_from_browser
from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(c):
    """Return the resource action specifications for the central registry."""
    return (
        ActionSpec(A.MATERIAL, "New Material", I.MATERIAL, c.resources.material),
        ActionSpec(
            A.MATERIAL_BROWSER,
            "Material Browser",
            I.MATERIAL,
            lambda: add_material_from_browser(c.resources),
        ),
        ActionSpec(A.SET_ELASTICITY, "Elasticity", I.ELASTICITY, lambda: c.resources.set_behavior("Elasticity")),
        ActionSpec(A.SET_DENSITY, "Density", I.DENSITY, lambda: c.resources.set_behavior("Density")),
        ActionSpec(A.SET_PLASTICITY, "Plasticity", I.PLASTICITY, lambda: c.resources.set_behavior("Plasticity")),
        ActionSpec(A.SET_THERMAL, "Expansion", I.THERMAL, lambda: c.resources.set_behavior("Thermal expansion")),
        ActionSpec(A.FIELD, "New Field", I.FIELD, c.resources.field),
        ActionSpec(A.SECTION_SOLID, "Solid", I.SECTION_SOLID, lambda: c.resources.section("Solid")),
        ActionSpec(A.SECTION_SHELL, "Shell", I.SECTION_SHELL, lambda: c.resources.section("Shell")),
        ActionSpec(A.SECTION_BEAM, "Beam", I.SECTION_BEAM, lambda: c.resources.section("Beam")),
        ActionSpec(A.SECTION_TRUSS, "Truss", I.SECTION_TRUSS, lambda: c.resources.section("Truss")),
        ActionSpec(A.PROFILE_RECTANGLE, "Rectangle", I.PROFILE_RECTANGLE, lambda: c.resources.profile("Rectangle")),
        ActionSpec(A.PROFILE_BOX, "Box", I.PROFILE_BOX, lambda: c.resources.profile("Box")),
        ActionSpec(A.PROFILE_PIPE, "Pipe", I.PROFILE_PIPE, lambda: c.resources.profile("Pipe")),
        ActionSpec(A.PROFILE_I, "I-Profile", I.PROFILE_I, lambda: c.resources.profile("I-profile")),
        ActionSpec(A.PROFILE_CHANNEL, "C-Profile", I.PROFILE_CHANNEL, lambda: c.resources.profile("C-profile")),
        ActionSpec(A.PROFILE_U, "U-Profile", I.PROFILE_U, lambda: c.resources.profile("U-profile")),
        ActionSpec(A.PROFILE_H, "H-Profile", I.PROFILE_H, lambda: c.resources.profile("H-profile")),
        ActionSpec(A.PROFILE_CIRCLE, "Circle", I.PROFILE_CIRCLE, lambda: c.resources.profile("Circle")),
        ActionSpec(A.PROFILE_GENERAL, "General", I.PROFILE_GENERAL, lambda: c.resources.profile("General")),
        ActionSpec(A.PROFILE_GRAPH, "Graph", I.PROFILE_GRAPH, lambda: c.resources.profile("Graph profile")),
    )
