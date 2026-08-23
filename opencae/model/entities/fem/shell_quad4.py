"""Defines a four-node quadrilateral shell element for public FEM authoring."""

from ..elements import QuadrilateralShellElementDefinition
from .element import Element


class ShellQuad4(Element):
    """Represents a four-node quadrilateral shell element."""

    node_count = 4
    definition_type = QuadrilateralShellElementDefinition
