"""Defines a four-node tetrahedral solid element for public FEM authoring."""

from ..elements import TetrahedronElementDefinition
from .element import Element


class Tet4(Element):
    """Represents a four-node tetrahedral solid element."""

    node_count = 4
    definition_type = TetrahedronElementDefinition
