"""Defines a three-node triangular shell element for public FEM authoring."""

from ..elements import TriangleShellElementDefinition
from .element import Element


class ShellTri3(Element):
    """Represents a three-node triangular shell element."""

    node_count = 3
    definition_type = TriangleShellElementDefinition
