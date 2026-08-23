"""Defines a two-node truss element for the public FEM authoring model."""

from ..elements import TrussElementDefinition
from .element import Element


class Truss2(Element):
    """Represents a two-node truss element."""

    node_count = 2
    definition_type = TrussElementDefinition
