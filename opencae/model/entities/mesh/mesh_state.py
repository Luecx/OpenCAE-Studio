"""Compatibility facade over separated meshing recipe, FE data and metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from ...core import EntityRef, register_model_type
from ..fem import Element, MeshEntityOrigin, Node, element_class_for_definition
from .element_block import ElementBlock
from .finite_element_mesh import FiniteElementMesh
from .mesh_associations import MeshAssociationStore
from .mesh_definition_registry import (
    bind_element_blocks,
    definition_for,
    refresh_definition_counts,
    replace_element_blocks,
)
from .mesh_lifecycle import (
    GeometryAssociationState,
    MeshEditState,
    MeshLifecycleState,
    MeshValidity,
)
from .mesh_quality import MeshQualitySummary
from .mesh_status import MeshStatus
from .meshing_recipe import MeshingRecipe


@register_model_type("mesh_state")
@dataclass(init=False)
class MeshState:
    """Part mesh aggregate composed from orthogonal persistent concerns.

    Persistence owns ``recipe``, ``finite_elements``, ``associations``,
    ``quality`` and ``lifecycle`` separately. Legacy attribute names remain as
    forwarding properties so existing meshing/rendering/solver code can migrate
    incrementally without creating a second source of truth.
    """

    recipe: MeshingRecipe
    finite_elements: FiniteElementMesh
    associations: MeshAssociationStore
    quality: MeshQualitySummary
    lifecycle: MeshLifecycleState

    def __init__(
        self,
        recipe: MeshingRecipe | None = None,
        finite_elements: FiniteElementMesh | None = None,
        associations: MeshAssociationStore | None = None,
        quality: MeshQualitySummary | None = None,
        lifecycle: MeshLifecycleState | None = None,
        **legacy,
    ) -> None:
        self.recipe = recipe or MeshingRecipe()
        self.finite_elements = finite_elements or FiniteElementMesh()
        self.associations = associations or MeshAssociationStore()
        self.quality = quality or MeshQualitySummary()
        self.lifecycle = lifecycle or MeshLifecycleState()

        aliases = {
            "settings": "settings",
            "seeds": "seeds",
            "element_controls": "element_controls",
            "element_definitions": "element_definitions",
            "nodes": "nodes",
            "element_blocks": "element_blocks",
            "entity_nodes": "entity_nodes",
            "entity_elements": "entity_elements",
            "entity_facets": "entity_facets",
            "node_count": "node_count",
            "element_count": "element_count",
            "mesh_dimension": "mesh_dimension",
            "minimum_quality": "minimum_quality",
            "mean_quality": "mean_quality",
            "status": "status",
            "revision": "revision",
        }
        unknown = set(legacy) - set(aliases)
        if unknown:
            raise TypeError(
                "Unexpected MeshState argument(s): " + ", ".join(sorted(unknown))
            )
        for name in aliases:
            if name in legacy:
                setattr(self, aliases[name], legacy[name])

        self.finite_elements.refresh_counts()
        bind_element_blocks(self)
        self._sync_association_state()

    @property
    def settings(self):
        return self.recipe.settings

    @settings.setter
    def settings(self, value):
        self.recipe.settings = value

    @property
    def seeds(self):
        return self.recipe.seeds

    @seeds.setter
    def seeds(self, value):
        self.recipe.seeds = list(value or ())

    @property
    def element_controls(self):
        return self.recipe.element_controls

    @element_controls.setter
    def element_controls(self, value):
        self.recipe.element_controls = list(value or ())

    @property
    def element_definitions(self):
        return self.finite_elements.element_definitions

    @element_definitions.setter
    def element_definitions(self, value):
        self.finite_elements.element_definitions = list(value or ())
        if hasattr(self, "finite_elements"):
            bind_element_blocks(self)

    @property
    def nodes(self):
        return self.finite_elements.nodes

    @nodes.setter
    def nodes(self, value):
        self.finite_elements.nodes = value
        self.finite_elements.node_count = len(value)

    @property
    def element_blocks(self):
        return self.finite_elements.element_blocks

    @element_blocks.setter
    def element_blocks(self, value):
        self.finite_elements.element_blocks = list(value or ())
        self.finite_elements.element_count = sum(
            len(block) for block in self.finite_elements.element_blocks
        )
        bind_element_blocks(self)

    @property
    def node_count(self):
        return self.finite_elements.node_count

    @node_count.setter
    def node_count(self, value):
        self.finite_elements.node_count = int(value or 0)

    @property
    def element_count(self):
        return self.finite_elements.element_count

    @element_count.setter
    def element_count(self, value):
        self.finite_elements.element_count = int(value or 0)

    @property
    def mesh_dimension(self):
        return self.finite_elements.mesh_dimension

    @mesh_dimension.setter
    def mesh_dimension(self, value):
        self.finite_elements.mesh_dimension = int(value or 0)

    @property
    def entity_nodes(self):
        return self.associations.nodes

    @entity_nodes.setter
    def entity_nodes(self, value):
        self.associations.nodes = self.associations.nodes.from_mapping(
            value,
            value_kind="ids",
        )
        self._sync_association_state()

    @property
    def entity_elements(self):
        return self.associations.elements

    @entity_elements.setter
    def entity_elements(self, value):
        self.associations.elements = self.associations.elements.from_mapping(
            value,
            value_kind="ids",
        )
        self._sync_association_state()

    @property
    def entity_facets(self):
        return self.associations.facets

    @entity_facets.setter
    def entity_facets(self, value):
        self.associations.facets = self.associations.facets.from_mapping(
            value,
            value_kind="facets",
        )
        self._sync_association_state()

    @property
    def minimum_quality(self):
        return self.quality.minimum

    @minimum_quality.setter
    def minimum_quality(self, value):
        self.quality.minimum = None if value is None else float(value)

    @property
    def mean_quality(self):
        return self.quality.mean

    @mean_quality.setter
    def mean_quality(self, value):
        self.quality.mean = None if value is None else float(value)

    @property
    def revision(self):
        return self.lifecycle.revision

    @revision.setter
    def revision(self, value):
        self.lifecycle.revision = str(value or "")

    @property
    def status(self) -> MeshStatus:
        if not self.nodes.ids and not self.element_blocks:
            return MeshStatus.NOT_GENERATED
        if self.lifecycle.validity is MeshValidity.OUTDATED:
            return MeshStatus.OUTDATED
        if self.lifecycle.origin is MeshEntityOrigin.AUTHORED:
            return MeshStatus.AUTHORED
        if self.lifecycle.edit_state in {
            MeshEditState.MODIFIED,
            MeshEditState.DETACHED,
        }:
            return MeshStatus.AUTHORED
        return MeshStatus.CURRENT

    @status.setter
    def status(self, value) -> None:
        status = MeshStatus.coerce(value)
        if status is MeshStatus.AUTHORED:
            self.lifecycle.origin = MeshEntityOrigin.AUTHORED
            self.lifecycle.edit_state = MeshEditState.MODIFIED
            self.lifecycle.validity = MeshValidity.CURRENT
        elif status is MeshStatus.CURRENT:
            self.lifecycle.validity = MeshValidity.CURRENT
        elif status is MeshStatus.OUTDATED:
            self.lifecycle.validity = MeshValidity.OUTDATED
        else:
            self.lifecycle.validity = MeshValidity.CURRENT
            self.lifecycle.edit_state = MeshEditState.CLEAN

    def definition_for(self, reference: EntityRef | str | None):
        return definition_for(self, reference)

    def replace_element_blocks(self, blocks: list[ElementBlock]) -> None:
        replace_element_blocks(self, blocks)
        self.finite_elements.refresh_counts()

    def refresh_element_definition_counts(self) -> None:
        refresh_definition_counts(self)

    def add_node(
        self,
        coordinates: Node | tuple[float, float, float],
        node_id: int | None = None,
        *,
        origin: MeshEntityOrigin | str = MeshEntityOrigin.AUTHORED,
    ) -> Node:
        was_empty = not self.nodes.ids and not self.element_blocks
        node = self.nodes.add(coordinates, node_id, origin)
        self.node_count = len(self.nodes)
        self._mark_modified(initial_origin=origin if was_empty else None)
        return node

    def next_element_id(self) -> int:
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
            self.element_blocks = [*self.element_blocks, block]
        block.add(element)
        self.element_count = sum(len(item) for item in self.element_blocks)
        refresh_definition_counts(self)
        self._mark_modified()
        from .mesh_validation import (
            MeshValidationReport,
            apply_local_validation,
            validate_element,
        )
        apply_local_validation(
            self,
            MeshValidationReport((validate_element(element),)),
        )
        return element

    def node(self, node_id: int) -> Node:
        return self.nodes.get(node_id)

    def element(self, element_id: int) -> Element:
        block = self._block_for_element(element_id)
        index = block.position(element_id)
        nodes = tuple(
            self.nodes.get(node_id) for node_id in block.connectivity[index]
        )
        element_type = element_class_for_definition(block.definition)
        return element_type(element_id, nodes, block.origins[index])

    def incident_element_ids(self, node_id: int) -> tuple[int, ...]:
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
        incident = self.incident_element_ids(node_id)
        from .mesh_validation import apply_local_validation, validate_node_move
        report = validate_node_move(self, node_id, coordinates)
        node = self.nodes.update(node_id, coordinates)
        detached = self._detach_from_geometry(
            node_ids=(node_id,),
            element_ids=incident,
        )
        self._mark_modified(detached=detached)
        apply_local_validation(self, report)
        return node

    def remove_node(self, node_id: int) -> Node:
        incident = self.incident_element_ids(node_id)
        if incident:
            joined = ", ".join(str(value) for value in incident[:8])
            suffix = "…" if len(incident) > 8 else ""
            raise ValueError(
                f"Node {node_id} is used by element(s) {joined}{suffix}; "
                "delete or reconnect those elements first"
            )
        node = self.nodes.remove(node_id)
        detached = self._detach_from_geometry(node_ids=(node_id,))
        self.node_count = len(self.nodes)
        self._mark_modified(detached=detached)
        return node

    def replace_element(
        self,
        element_id: int,
        element_type: type[Element],
        nodes: tuple[Node, ...] | list[Node],
    ) -> Element:
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
        detached = self._detach_from_geometry(element_ids=(element_id,))
        refresh_definition_counts(self)
        self._mark_modified(detached=detached)
        from .mesh_validation import (
            MeshValidationReport,
            apply_local_validation,
            validate_element,
        )
        apply_local_validation(
            self,
            MeshValidationReport((validate_element(after),)),
        )
        return after

    def remove_element(self, element_id: int) -> Element:
        element = self.element(element_id)
        block = self._block_for_element(element_id)
        block.remove(element_id)
        self._remove_empty_block(block)
        detached = self._detach_from_geometry(element_ids=(element_id,))
        self.element_count = sum(len(item) for item in self.element_blocks)
        refresh_definition_counts(self)
        self._mark_modified(detached=detached)
        from .mesh_validation import forget_element_validation
        forget_element_validation(self, element_id)
        return element

    def _block_for_element(self, element_id: int) -> ElementBlock:
        matches = [
            block
            for block in self.element_blocks
            if int(element_id) in block.ids
        ]
        if not matches:
            raise KeyError(f"Element {element_id} does not exist")
        if len(matches) > 1:
            raise ValueError(
                f"Element id {element_id} exists in multiple blocks"
            )
        return matches[0]

    def _remove_empty_block(self, block: ElementBlock) -> None:
        if len(block):
            return
        blocks = [value for value in self.element_blocks if value is not block]
        self.element_blocks = blocks
        referenced = {item.definition_ref.entity_id for item in blocks}
        self.element_definitions = [
            definition
            for definition in self.element_definitions
            if definition.id in referenced
        ]
        bind_element_blocks(self)

    def _detach_from_geometry(self, *, node_ids=(), element_ids=()) -> bool:
        changed = self.associations.detach(
            node_ids=node_ids,
            element_ids=element_ids,
        )
        if changed:
            self.lifecycle.geometry_association = GeometryAssociationState.DETACHED
        return changed

    def _mark_modified(self, *, detached=False, initial_origin=None) -> None:
        if initial_origin is not None:
            self.lifecycle.origin = MeshEntityOrigin.coerce(initial_origin)
        self.lifecycle.mark_modified(detached=detached)
        self.quality.minimum = None
        self.quality.mean = None

    def _sync_association_state(self) -> None:
        if self.associations.empty:
            if (
                self.lifecycle.geometry_association
                is GeometryAssociationState.ATTACHED
            ):
                self.lifecycle.geometry_association = GeometryAssociationState.NONE
        elif self.lifecycle.geometry_association is GeometryAssociationState.NONE:
            self.lifecycle.geometry_association = GeometryAssociationState.ATTACHED

    def iter_elements(self) -> Iterator[Element]:
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
