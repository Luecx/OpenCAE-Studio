"""Create and enumerate canonical OpenCAE element-definition classes."""

from .base import ElementDefinition
from .beam import BeamElementDefinition
from .hexahedron import HexahedronElementDefinition
from .line import LineElementDefinition
from .pentahedron import PentahedronElementDefinition
from .pyramid import PyramidElementDefinition
from .quadrilateral_2d import Quadrilateral2DElementDefinition
from .quadrilateral_shell import QuadrilateralShellElementDefinition
from .tetrahedron import TetrahedronElementDefinition
from .triangle_2d import Triangle2DElementDefinition
from .triangle_shell import TriangleShellElementDefinition
from .truss import TrussElementDefinition

_TYPES = {
    ("Line Elements", "Lines"): LineElementDefinition,
    ("Line Elements", "Beam Elements"): BeamElementDefinition,
    ("Line Elements", "Truss Elements"): TrussElementDefinition,
    ("Shell Elements", "Triangles"): TriangleShellElementDefinition,
    ("Shell Elements", "Quadrilaterals"): QuadrilateralShellElementDefinition,
    ("2D Elements", "Triangles"): Triangle2DElementDefinition,
    ("2D Elements", "Quadrilaterals"): Quadrilateral2DElementDefinition,
    ("Solid Elements", "Tetrahedra"): TetrahedronElementDefinition,
    ("Solid Elements", "Pyramids"): PyramidElementDefinition,
    ("Solid Elements", "Pentahedra"): PentahedronElementDefinition,
    ("Solid Elements", "Hexahedra"): HexahedronElementDefinition,
}


def element_definition_types() -> tuple[tuple[str, str, type[ElementDefinition]], ...]:
    """Return canonical element families in their stable UI/export ordering."""
    return tuple(
        (category, topology, definition_type)
        for (category, topology), definition_type in _TYPES.items()
    )


def create_element_definition(category: str, topology: str, **kwargs) -> ElementDefinition:
    """Create the registered element-definition class for one family/topology."""
    cls = _TYPES.get((category, topology), ElementDefinition)
    if cls is ElementDefinition:
        return cls(category=category, topology=topology, **kwargs)
    return cls(**kwargs)
