"""Defines the base authored finite-element value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..elements.base import ElementDefinition
from .node import Node


@dataclass(frozen=True, slots=True)
class Element:
    """One authored finite element with object-based Node connectivity."""

    id: int
    nodes: tuple[Node, ...]

    node_count: ClassVar[int | None] = None
    definition_type: ClassVar[type[ElementDefinition]] = ElementDefinition

    def __post_init__(self) -> None:
        """Normalize identity/connectivity and reject invalid elements."""
        element_id = int(self.id)
        if element_id <= 0:
            raise ValueError("Element ids must be positive integers")

        nodes = tuple(self.nodes)
        if not all(isinstance(node, Node) for node in nodes):
            raise TypeError("Element connectivity must contain Node objects")
        if self.node_count is not None and len(nodes) != self.node_count:
            raise ValueError(
                f"{type(self).__name__} requires {self.node_count} nodes, "
                f"got {len(nodes)}"
            )

        # Duplicate connectivity is rejected here rather than in exporters so an
        # impossible authored element can never enter a Part mesh.
        if len({node.id for node in nodes}) != len(nodes):
            raise ValueError("An element cannot contain the same node twice")

        object.__setattr__(self, "id", element_id)
        object.__setattr__(self, "nodes", nodes)

    @property
    def connectivity(self) -> tuple[int, ...]:
        """Return solver-style node IDs without exposing string references."""
        return tuple(node.id for node in self.nodes)

    @classmethod
    def definition(cls) -> ElementDefinition:
        """Create the mesher/solver definition associated with this element."""
        return cls.definition_type(name=cls.__name__)
