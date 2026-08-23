"""Defines a six-node wedge solid element for public FEM authoring."""

from ..elements import PentahedronElementDefinition
from .element import Element


class Wedge6(Element):
    """Represents a six-node wedge solid element."""

    node_count = 6
    definition_type = PentahedronElementDefinition
