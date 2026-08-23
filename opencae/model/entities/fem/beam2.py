"""Defines a two-node beam element for the public FEM authoring model."""

from ..elements import BeamElementDefinition
from .element import Element


class Beam2(Element):
    """Represents a two-node beam element."""

    node_count = 2
    definition_type = BeamElementDefinition
