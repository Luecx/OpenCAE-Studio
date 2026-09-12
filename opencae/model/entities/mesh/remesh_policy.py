"""Explicit remeshing rules for meshes containing non-generated entities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ...core import register_model_type
from ..fem import MeshEntityOrigin
from .mesh_associations import MeshAssociationStore
from .mesh_lifecycle import (
    GeometryAssociationState,
    MeshEditState,
    MeshValidity,
)


class RemeshReplacementMode(StrEnum):
    REPLACE_ALL = "replace_all"
    REPLACE_GENERATED = "replace_generated"


class RemeshAssociationMode(StrEnum):
    REBUILD = "rebuild"
    DISCARD = "discard"


@register_model_type("remesh_policy")
@dataclass(frozen=True, slots=True)
class RemeshPolicy:
    """Describe what survives one CAD remesh operation."""

    replacement: RemeshReplacementMode | str = RemeshReplacementMode.REPLACE_ALL
    preserve_origins: tuple[MeshEntityOrigin | str, ...] = (
        MeshEntityOrigin.AUTHORED,
        MeshEntityOrigin.IMPORTED,
    )
    associations: RemeshAssociationMode | str = RemeshAssociationMode.REBUILD
    convert_to_authored: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "replacement",
            RemeshReplacementMode(self.replacement),
        )
        object.__setattr__(
            self,
            "preserve_origins",
            tuple(
                MeshEntityOrigin.coerce(value)
                for value in self.preserve_origins
            ),
        )
        object.__setattr__(
            self,
            "associations",
            RemeshAssociationMode(self.associations),
        )
        object.__setattr__(
            self,
            "convert_to_authored",
            bool(self.convert_to_authored),
        )

    @classmethod
    def replace_all(cls) -> "RemeshPolicy":
        return cls(RemeshReplacementMode.REPLACE_ALL)


def requires_remesh_decision(mesh) -> bool:
    """Return whether remeshing can destroy authored/imported FE data."""
    preserved = {MeshEntityOrigin.AUTHORED, MeshEntityOrigin.IMPORTED}
    if any(origin in preserved for origin in mesh.nodes.origins):
        return True
    return any(
        origin in preserved
        for block in mesh.element_blocks
        for origin in block.origins
    )


def merge_remesh_result(
    existing,
    generated,
    policy: RemeshPolicy | None = None,
):
    """Apply an explicit remesh policy to a generated candidate in-place."""
    policy = policy or RemeshPolicy.replace_all()
    generated.lifecycle.mark_generated(
        revision=generated.revision,
        associated=not generated.associations.empty,
    )

    if policy.replacement is RemeshReplacementMode.REPLACE_GENERATED:
        _preserve_non_generated(
            existing,
            generated,
            set(policy.preserve_origins),
        )

    if policy.associations is RemeshAssociationMode.DISCARD:
        generated.associations = MeshAssociationStore()
        generated.lifecycle.geometry_association = GeometryAssociationState.NONE

    if policy.convert_to_authored:
        generated.nodes.origins = [
            MeshEntityOrigin.AUTHORED
        ] * len(generated.nodes.ids)
        for block in generated.element_blocks:
            block.origins = [MeshEntityOrigin.AUTHORED] * len(block.ids)
        generated.associations = MeshAssociationStore()
        generated.lifecycle.origin = MeshEntityOrigin.AUTHORED
        generated.lifecycle.edit_state = MeshEditState.DETACHED
        generated.lifecycle.validity = MeshValidity.CURRENT
        generated.lifecycle.geometry_association = (
            GeometryAssociationState.DETACHED
        )
    elif (
        policy.replacement is RemeshReplacementMode.REPLACE_GENERATED
        and requires_remesh_decision(existing)
    ):
        generated.lifecycle.edit_state = MeshEditState.MODIFIED

    generated.finite_elements.refresh_counts()
    generated.refresh_element_definition_counts()
    return generated


def _preserve_non_generated(
    existing,
    generated,
    preserve_origins: set[MeshEntityOrigin],
) -> None:
    preserved_elements = [
        element
        for element in existing.iter_elements()
        if element.origin in preserve_origins
    ]
    required_node_ids = {
        node.id
        for element in preserved_elements
        for node in element.nodes
    }
    required_node_ids.update(
        node.id
        for node in existing.nodes
        if node.origin in preserve_origins
    )
    preserved_nodes = [
        existing.node(node_id)
        for node_id in existing.nodes.ids
        if node_id in required_node_ids
    ]

    reserved_node_ids = {node.id for node in preserved_nodes}
    node_remap = _remap_generated_node_collisions(
        generated,
        reserved_node_ids,
    )
    if node_remap:
        _remap_generated_connectivity(generated, node_remap)
        _remap_association_ids(generated.entity_nodes, node_remap)

    reserved_element_ids = {element.id for element in preserved_elements}
    element_remap = _remap_generated_element_collisions(
        generated,
        reserved_element_ids,
    )
    if element_remap:
        _remap_association_ids(generated.entity_elements, element_remap)
        _remap_facet_associations(generated.entity_facets, element_remap)

    existing_node_ids = set(generated.nodes.ids)
    for node in preserved_nodes:
        if node.id not in existing_node_ids:
            generated.nodes.add(node)
            existing_node_ids.add(node.id)

    for element in preserved_elements:
        nodes = tuple(generated.node(node.id) for node in element.nodes)
        generated.add_element(
            type(element),
            nodes,
            element.id,
            origin=element.origin,
        )


def _remap_generated_node_collisions(mesh, reserved: set[int]) -> dict[int, int]:
    used = set(mesh.nodes.ids) | set(reserved)
    next_id = max(used, default=0) + 1
    mapping: dict[int, int] = {}
    for index, node_id in enumerate(list(mesh.nodes.ids)):
        if node_id not in reserved:
            continue
        while next_id in used:
            next_id += 1
        mapping[node_id] = next_id
        mesh.nodes.ids[index] = next_id
        used.add(next_id)
        next_id += 1
    return mapping


def _remap_generated_connectivity(mesh, mapping: dict[int, int]) -> None:
    for block in mesh.element_blocks:
        block.connectivity = [
            tuple(mapping.get(node_id, node_id) for node_id in row)
            for row in block.connectivity
        ]


def _remap_generated_element_collisions(
    mesh,
    reserved: set[int],
) -> dict[int, int]:
    used = {
        element_id
        for block in mesh.element_blocks
        for element_id in block.ids
    } | set(reserved)
    next_id = max(used, default=0) + 1
    mapping: dict[int, int] = {}
    for block in mesh.element_blocks:
        for index, element_id in enumerate(list(block.ids)):
            if element_id not in reserved:
                continue
            while next_id in used:
                next_id += 1
            mapping[element_id] = next_id
            block.ids[index] = next_id
            used.add(next_id)
            next_id += 1
    return mapping


def _remap_association_ids(mapping_store, remap: dict[int, int]) -> None:
    for key in list(mapping_store):
        mapping_store[key] = [
            remap.get(int(value), int(value))
            for value in mapping_store[key]
        ]


def _remap_facet_associations(mapping_store, remap: dict[int, int]) -> None:
    for key in list(mapping_store):
        mapping_store[key] = [
            (remap.get(int(element_id), int(element_id)), local_face)
            for element_id, local_face in mapping_store[key]
        ]
