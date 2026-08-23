"""Defines a four-node planar continuum element for public FEM authoring."""

from ..elements import Quadrilateral2DElementDefinition
from .element import Element


class PlaneQuad4(Element):
    """Represents a four-node planar continuum element."""

    node_count = 4
    definition_type = Quadrilateral2DElementDefinition
