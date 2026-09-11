"""Finite-element data storage independent from CAD and meshing recipe state."""

from dataclasses import dataclass, field

from ...core import register_model_type
from ..elements.base import ElementDefinition
from .element_block import ElementBlock
from .node_table import NodeTable


@register_model_type("finite_element_mesh")
@dataclass
class FiniteElementMesh:
    """Own nodes, elements and their canonical definitions."""

    nodes: NodeTable = field(
        default_factory=NodeTable,
        metadata={"project_index": False},
    )
    element_definitions: list[ElementDefinition] = field(default_factory=list)
    element_blocks: list[ElementBlock] = field(default_factory=list)
    node_count: int = 0
    element_count: int = 0
    mesh_dimension: int = 0

    def refresh_counts(self) -> None:
        self.node_count = len(self.nodes)
        self.element_count = sum(len(block) for block in self.element_blocks)
