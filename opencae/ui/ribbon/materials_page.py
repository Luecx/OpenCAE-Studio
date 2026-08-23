"""Defines the Materials workflow ribbon groups."""

from opencae.ui.actions.ids import A
from .specs import RibbonGroupSpec


def groups():
    """Return material creation/library and behavior-definition groups."""
    return (
        RibbonGroupSpec("MATERIAL", (A.MATERIAL, A.MATERIAL_BROWSER)),
        RibbonGroupSpec(
            "DEFINITIONS",
            (
                A.SET_ELASTICITY,
                A.SET_DENSITY,
                A.SET_PLASTICITY,
                A.SET_THERMAL,
            ),
        ),
    )
