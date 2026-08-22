from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..elements import (
    BeamElementDefinition,
    HexahedronElementDefinition,
    LineElementDefinition,
    PentahedronElementDefinition,
    PyramidElementDefinition,
    Quadrilateral2DElementDefinition,
    QuadrilateralShellElementDefinition,
    TetrahedronElementDefinition,
    Triangle2DElementDefinition,
    TriangleShellElementDefinition,
    TrussElementDefinition,
)
from ..elements.base import ElementDefinition
from .node import Node


@dataclass(frozen=True, slots=True)
class Element:
    """Base class for one authored finite element."""

    id: int
    nodes: tuple[Node, ...]

    node_count: ClassVar[int | None] = None
    definition_type: ClassVar[type[ElementDefinition]] = ElementDefinition

    def __post_init__(self):
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
        if len({node.id for node in nodes}) != len(nodes):
            raise ValueError("An element cannot contain the same node twice")
        object.__setattr__(self, "id", element_id)
        object.__setattr__(self, "nodes", nodes)

    @property
    def connectivity(self) -> tuple[int, ...]:
        return tuple(node.id for node in self.nodes)

    @classmethod
    def definition(cls) -> ElementDefinition:
        return cls.definition_type(name=cls.__name__)


class Line2(Element):
    node_count = 2
    definition_type = LineElementDefinition


class Beam2(Element):
    node_count = 2
    definition_type = BeamElementDefinition


class Truss2(Element):
    node_count = 2
    definition_type = TrussElementDefinition


class ShellTri3(Element):
    node_count = 3
    definition_type = TriangleShellElementDefinition


class ShellQuad4(Element):
    node_count = 4
    definition_type = QuadrilateralShellElementDefinition


class PlaneTri3(Element):
    node_count = 3
    definition_type = Triangle2DElementDefinition


class PlaneQuad4(Element):
    node_count = 4
    definition_type = Quadrilateral2DElementDefinition


class Tet4(Element):
    node_count = 4
    definition_type = TetrahedronElementDefinition


class Pyramid5(Element):
    node_count = 5
    definition_type = PyramidElementDefinition


class Wedge6(Element):
    node_count = 6
    definition_type = PentahedronElementDefinition


class Hex8(Element):
    node_count = 8
    definition_type = HexahedronElementDefinition


ELEMENT_TYPES: tuple[type[Element], ...] = (
    Line2,
    Beam2,
    Truss2,
    ShellTri3,
    ShellQuad4,
    PlaneTri3,
    PlaneQuad4,
    Tet4,
    Pyramid5,
    Wedge6,
    Hex8,
)


def element_class_for_definition(definition: ElementDefinition) -> type[Element]:
    for cls in ELEMENT_TYPES:
        if isinstance(definition, cls.definition_type):
            return cls
    return Element
