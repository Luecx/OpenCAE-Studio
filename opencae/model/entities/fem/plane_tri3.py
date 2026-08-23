"""Defines a three-node planar continuum element for public FEM authoring."""

from ..elements import Triangle2DElementDefinition
from .element import Element


class PlaneTri3(Element):
    """Represents a three-node planar continuum element."""

    node_count = 3
    definition_type = Triangle2DElementDefinition
