from .coordinate_system import CoordinateSystem
from .element_set import ElementSet as _LegacyElementSet
from .factory import create_region
from .node_set import NodeSet as _LegacyNodeSet
from .orientation import Orientation
from .reference_point import ReferencePoint
from .region import (
    ElementRegion,
    GeometryRegion,
    NodeRegion,
    Region,
    SurfaceRegion,
)
from .section_assignment import SectionAssignment
from .surface import Surface as _LegacySurface

__all__ = [
    "CoordinateSystem",
    "Orientation",
    "ReferencePoint",
    "Region",
    "GeometryRegion",
    "NodeRegion",
    "ElementRegion",
    "SurfaceRegion",
    "SectionAssignment",
    "create_region",
]
