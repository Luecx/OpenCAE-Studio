"""Defines a five-node pyramid solid element for public FEM authoring."""

from ..elements import PyramidElementDefinition
from .element import Element


class Pyramid5(Element):
    """Represents a five-node pyramid solid element."""

    node_count = 5
    definition_type = PyramidElementDefinition
