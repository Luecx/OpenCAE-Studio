"""Owns meshing configuration and the compact mesh snapshot of one Part."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from ...core import EntityRef, register_model_type
from ..elements.base import ElementDefinition
from ..fem import (
    Element,
    MeshEntityOrigin,
    Node,
    element_class_for_definition,
)
from .element_block import ElementBlock
from .element_control import ElementControl
from .mesh_definition_registry import (
    bind_element_blocks,
    definition_for,
    refresh_definition_counts,
    replace_element_blocks,
)
from .mesh_settings import MeshSettings
from .mesh_status import MeshStatus
from .node_table import NodeTable
from .seed import Seed


@register_model_type("mesh_state")
@dataclass
class MeshState:
    """Meshing configuration plus compact generated/authored mesh data."""

    settings: MeshSettings = field(
        default_factory=MeshSettings,
        metadata={"project_index": False},
    )
    seeds: list[Seed] = field(default_factory=list)
    element_controls: list[ElementControl] = field(default_factory=list)
    element_definitions: list[ElementDefinition] = field(default_factory=list)
    nodes: NodeTable = field(
        default_factory=NodeTable,
        metadata={"project_index": False},
    )
    element_blocks: list[ElementBlock] = field(default_factory=list)
    entity_nodes: dict[str, list[int]] = field(
        default_factory=dict,
        metadata={"project_index": False},
    )
    entity_elements: dict[str, list[int]] = field(
        default_factory=dict,
        metadata={"project_index": False},
    )
    entity_facets: dict[str, list[tuple[int, str]]] = field(
        default_factory=dict,
        metadata={"project_index": False},
    )
    node_count: int = 0
    element_count: int = 0
    mesh_dimension: int = 0
    minimum_quality: float | None = None
    mean_quality: float | None = None
    status: MeshStatus | str = MeshStatus.NOT_GENERATED
    revision: str = ""

    def __post_init__(self) -> None:
        """Bind compact blocks to the canonical definition collection."""
        bind_element_blocks(self)

    def __setattr__(self, name, value) -> None:
        """Normalize finite-domain state and bind replacement block collections."""
        if name == "status":
            value = MeshStatus.coerce(value)
        if name == "element_blocks":
            value = list(value)
            super().__setattr__(name, value)
            if "element_definitions" in self.__dict__:
                bind_element_blocks(self)
            return
        super().__setattr__(name, value)

    def definition_for(
        self,
        reference: EntityRef | str | None,
    ) -> ElementDefinition | None:
        """Resolve one block definition reference within this MeshState."""
        return definition_for(self, reference)

    def replace_element_blocks(self, blocks: list[ElementBlock]) -> None:
        """Replace generated blocks and rebuild the canonical definition set."""
        replace_element_blocks(self, blocks)

    def refresh_element_definition_counts(self) -> None:
        """Synchronize definition summary counts from compact block membership."""
        refresh_definition_counts(self)

    def add_node(
        self,
        coordinates: Node | tuple[float, float, float],
        node_id: int | None = None,
        *,
        origin: MeshEntityOrigin | str = MeshEntityOrigin.AUTHORED,
    ) -> Node:
        """Add one authored Node and update compact mesh metadata."""
        node = self.nodes.add(coordinates, node_id, origin)
        self.node_count = len(self.nodes)
        self._mark_authored()
        return node

    def next_element_id(self) -> int:
        """Return the next positive element ID across all compact blocks."""
        return max(
            (
                element_id
                for block in self.element_blocks
                for element_id in block.ids
            ),
            default=0,
        ) + 1

    def add_element(
        self,
        element_type: type[Element],
        nodes: tuple[Node, ...] | list[Node],
        element_id: int | None = None,
        *,
        origin: MeshEntityOrigin | str = MeshEntityOrigin.AUTHORED,
    ) -> Element:
        """Add one authored Element after validating type and node ownership."""
        if not isinstance(element_type, type) or not issubclass(
            element_type,
            Element,
        ):
            raise TypeError("element_type must be an Element subclass")

        element = element_type(
            element_id or self.next_element_id(),
            tuple(nodes),
            origin,
        )
        if any(element.id in block.ids for block in self.element_blocks):
            raise ValueError(f"Element id {element.id} already exists")
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
            block = ElementBlock(element_type.definition())
            self.element_blocks.append(block)
            bind_element_blocks(self)

        block.add(element)
        self.element_count = sum(len(item) for item in self.element_blocks)
        refresh_definition_counts(self)
        self._mark_authored()
        return element

    def node(self, node_id: int) -> Node:
        """Return one current node value by stable positive ID."""
        return self.nodes.get(node_id)

    def element(self, element_id: int) -> Element:
        """Return one current element value reconstructed from compact storage."""
        block = self._block_for_element(element_id)
        index = block.position(element_id)
        nodes = tuple(self.nodes.get(node_id) for node_id in block.connectivity[index])
        element_type = element_class_for_definition(block.definition)
        return element_type(element_id, nodes, block.origins[index])

    def incident_element_ids(self, node_id: int) -> tuple[int, ...]:
        """Return all elements whose connectivity contains the requested node."""
        node_id = int(node_id)
        return tuple(
            element_id
            for block in self.element_blocks
            for element_id, connectivity in zip(
                block.ids,
                block.connectivity,
                strict=True,
            )
            if node_id in connectivity
        )

    def move_node(
        self,
        node_id: int,
        coordinates: tuple[float, float, float],
    ) -> Node:
        """Move one node, detach affected CAD membership, and invalidate quality."""
        incident = self.incident_element_ids(node_id)
        node = self.nodes.update(node_id, coordinates)
        self._detach_from_geometry(node_ids=(node_id,), element_ids=incident)
        self._mark_authored()
        return node

    def remove_node(self, node_id: int) -> Node:
        """Remove an unused node while refusing dangling element connectivity."""
        incident = self.incident_element_ids(node_id)
        if incident:
            joined = ", ".join(str(value) for value in incident[:8])
            suffix = "…" if len(incident) > 8 else ""
            raise ValueError(
                f"Node {node_id} is used by element(s) {joined}{suffix}; "
                "delete or reconnect those elements first"
            )
        node = self.nodes.remove(node_id)
        self._detach_from_geometry(node_ids=(node_id,))
        self.node_count = len(self.nodes)
        self._mark_authored()
        return node

    def replace_element(
        self,
        element_id: int,
        element_type: type[Element],
        nodes: tuple[Node, ...] | list[Node],
    ) -> Element:
        """Replace one element's type/connectivity while preserving its ID."""
        before_block = self._block_for_element(element_id)
        after = element_type(
            int(element_id),
            tuple(nodes),
            MeshEntityOrigin.AUTHORED,
        )
        owned_ids = set(self.nodes.ids)
        missing = [node.id for node in after.nodes if node.id not in owned_ids]
        if missing:
            raise ValueError(f"Element references missing node ids: {missing}")

        if isinstance(before_block.definition, element_type.definition_type):
            before_block.replace(after)
        else:
            before_block.remove(element_id)
            self._remove_empty_block(before_block)
            self.add_element(
                element_type,
                after.nodes,
                element_id,
                origin=MeshEntityOrigin.AUTHORED,
            )
        self._detach_from_geometry(element_ids=(element_id,))
        refresh_definition_counts(self)
        self._mark_authored()
        return after

    def remove_element(self, element_id: int) -> Element:
        """Remove one element and all of its optional CAD associations."""
        element = self.element(element_id)
        block = self._block_for_element(element_id)
        block.remove(element_id)
        self._remove_empty_block(block)
        self._detach_from_geometry(element_ids=(element_id,))
        self.element_count = sum(len(item) for item in self.element_blocks)
        refresh_definition_counts(self)
        self._mark_authored()
        return element

    def _block_for_element(self, element_id: int) -> ElementBlock:
        """Return the unique compact block containing an element ID."""
        matches = [
            block for block in self.element_blocks if int(element_id) in block.ids
        ]
        if not matches:
            raise KeyError(f"Element {element_id} does not exist")
        if len(matches) > 1:
            raise ValueError(f"Element id {element_id} exists in multiple blocks")
        return matches[0]

    def _remove_empty_block(self, block: ElementBlock) -> None:
        """Drop empty compact blocks and their now-unreferenced definitions."""
        if len(block):
            return
        self.element_blocks.remove(block)
        referenced = {
            item.definition_ref.entity_id for item in self.element_blocks
        }
        self.element_definitions = [
            definition
            for definition in self.element_definitions
            if definition.id in referenced
        ]
        bind_element_blocks(self)

    def _detach_from_geometry(self, *, node_ids=(), element_ids=()) -> None:
        """Remove optional CAD membership for manually changed mesh objects."""
        nodes = {int(value) for value in node_ids}
        elements = {int(value) for value in element_ids}
        if nodes:
            self.entity_nodes = {
                key: [value for value in values if int(value) not in nodes]
                for key, values in self.entity_nodes.items()
            }
        if elements:
            self.entity_elements = {
                key: [value for value in values if int(value) not in elements]
                for key, values in self.entity_elements.items()
            }
            self.entity_facets = {
                key: [
                    value for value in values if int(value[0]) not in elements
                ]
                for key, values in self.entity_facets.items()
            }

    def _mark_authored(self) -> None:
        """Invalidate derived quality and mark a mesh containing manual edits."""
        self.status = MeshStatus.AUTHORED
        self.minimum_quality = None
        self.mean_quality = None

    def iter_elements(self) -> Iterator[Element]:
        """Yield authored Element objects reconstructed from compact blocks."""
        nodes = {node.id: node for node in self.nodes}
        for block in self.element_blocks:
            element_type = element_class_for_definition(block.definition)
            for element_id, connectivity, origin in zip(
                block.ids,
                block.connectivity,
                block.origins,
                strict=True,
            ):
                try:
                    element_nodes = tuple(
                        nodes[node_id] for node_id in connectivity
                    )
                except KeyError as exc:
                    raise ValueError(
                        f"Element {element_id} references missing node "
                        f"{exc.args[0]}"
                    ) from exc
                yield element_type(element_id, element_nodes, origin)
