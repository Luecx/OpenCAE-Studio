"""Defines a two-node line element for the public FEM authoring model."""

from ..elements import LineElementDefinition
from .element import Element


class Line2(Element):
    """Represents a two-node line element."""

    node_count = 2
    definition_type = LineElementDefinition
