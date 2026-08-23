"""Maps authored Element classes to mesher/solver element definitions."""

from __future__ import annotations

from ..elements.base import ElementDefinition
from .beam2 import Beam2
from .element import Element
from .hex8 import Hex8
from .line2 import Line2
from .plane_quad4 import PlaneQuad4
from .plane_tri3 import PlaneTri3
from .pyramid5 import Pyramid5
from .shell_quad4 import ShellQuad4
from .shell_tri3 import ShellTri3
from .tet4 import Tet4
from .truss2 import Truss2
from .wedge6 import Wedge6

ELEMENT_TYPES: tuple[type[Element], ...] = (
    Line2,
    Beam2,
    Truss2,
    ShellTri3,
    ShellQuad4,
    PlaneTri3,
    PlaneQuad4,
    Tet4,
    Pyramid5,
    Wedge6,
    Hex8,
)


def element_class_for_definition(
    definition: ElementDefinition,
) -> type[Element]:
    """Return the authored class matching a mesher/solver definition."""
    for element_type in ELEMENT_TYPES:
        if isinstance(definition, element_type.definition_type):
            return element_type

    # Unknown/custom definitions still map to the generic Element so imported
    # meshes remain representable without inventing a wrong concrete topology.
    return Element
