from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from ...core import register_model_type
from ..elements.base import ElementDefinition
from ..fem import Element, Node, element_class_for_definition
from .element_block import ElementBlock
from .element_control import ElementControl
from .mesh_settings import MeshSettings
from .node_table import NodeTable
from .seed import Seed


@register_model_type("mesh_state")
@dataclass
class MeshState:
    """Meshing configuration plus compact generated/authored mesh data."""

    settings: MeshSettings = field(default_factory=MeshSettings)
    seeds: list[Seed] = field(default_factory=list)
    element_controls: list[ElementControl] = field(default_factory=list)
    elements: list[ElementDefinition] = field(default_factory=list)
    nodes: NodeTable = field(default_factory=NodeTable)
    element_blocks: list[ElementBlock] = field(default_factory=list)
    entity_nodes: dict[str, list[int]] = field(default_factory=dict)
    entity_elements: dict[str, list[int]] = field(default_factory=dict)
    entity_facets: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    node_count: int = 0
    element_count: int = 0
    mesh_dimension: int = 0
    minimum_quality: float | None = None
    mean_quality: float | None = None
    status: str = "Not generated"
    revision: str = ""

    def add_node(
        self,
        coordinates: tuple[float, float, float],
        node_id: int | None = None,
    ) -> Node:
        node = self.nodes.add(coordinates, node_id)
        self.node_count = len(self.nodes)
        if self.status == "Not generated":
            self.status = "Authored"
        return node

    def next_element_id(self) -> int:
        return max(
            (element_id for block in self.element_blocks for element_id in block.ids),
            default=0,
        ) + 1

    def add_element(
        self,
        element_type: type[Element],
        nodes: tuple[Node, ...] | list[Node],
        element_id: int | None = None,
    ) -> Element:
        if not isinstance(element_type, type) or not issubclass(element_type, Element):
            raise TypeError("element_type must be an Element subclass")
        element = element_type(element_id or self.next_element_id(), tuple(nodes))
        node_ids = set(self.nodes.ids)
        missing = [node.id for node in element.nodes if node.id not in node_ids]
        if missing:
            raise ValueError(
                "All element nodes must belong to the mesh first; "
                f"missing node ids: {missing}"
            )

        block = next(
            (
                item
                for item in self.element_blocks
                if isinstance(item.definition, element_type.definition_type)
            ),
            None,
        )
        if block is None:
            definition = element_type.definition()
            self.elements.append(definition)
            block = ElementBlock(definition)
            self.element_blocks.append(block)
        block.add(element)
        self.element_count = sum(len(item) for item in self.element_blocks)
        if self.status == "Not generated":
            self.status = "Authored"
        return element

    def iter_elements(self) -> Iterator[Element]:
        nodes = {node.id: node for node in self.nodes}
        for block in self.element_blocks:
            cls = element_class_for_definition(block.definition)
            for element_id, connectivity in zip(
                block.ids, block.connectivity, strict=True
            ):
                try:
                    element_nodes = tuple(nodes[node_id] for node_id in connectivity)
                except KeyError as exc:
                    raise ValueError(
                        f"Element {element_id} references missing node {exc.args[0]}"
                    ) from exc
                yield cls(element_id, element_nodes)
