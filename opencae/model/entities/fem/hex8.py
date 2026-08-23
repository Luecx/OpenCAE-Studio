"""Defines an eight-node hexahedral solid element for public FEM authoring."""

from ..elements import HexahedronElementDefinition
from .element import Element


class Hex8(Element):
    """Represents an eight-node hexahedral solid element."""

    node_count = 8
    definition_type = HexahedronElementDefinition
