"""Persists generated geometry-service mesh snapshots into Part mesh state."""

from opencae.geometry.element_summary import definition_from_block
from opencae.model.entities.fem import MeshEntityOrigin
from opencae.model.entities.mesh import (
    GeometryAssociationState,
    MeshEditState,
    MeshValidity,
)
from opencae.model.entities.parts import PartSourceKind
from opencae.model.mesh import ElementBlock, NodeTable
from opencae.model.selection import element_side_indices


def apply_mesh_snapshot(candidate, snapshot) -> None:
    """Replace FE payload and initialize orthogonal lifecycle state."""
    origin = (
        MeshEntityOrigin.IMPORTED
        if candidate.source_type is PartSourceKind.ORPHAN_MESH
        else MeshEntityOrigin.GENERATED
    )
    candidate.mesh.nodes = NodeTable(
        ids=[int(value) for value in snapshot.node_tags],
        coordinates=[tuple(map(float, row)) for row in snapshot.points],
        origins=[origin] * len(snapshot.node_tags),
    )
    candidate.mesh.entity_nodes = {
        key: list(values) for key, values in snapshot.entity_nodes.items()
    }
    candidate.mesh.entity_elements = {
        key: list(values) for key, values in snapshot.entity_elements.items()
    }
    candidate.mesh.entity_facets = {}

    blocks = []
    next_id = 1
    for block in snapshot.blocks:
        if block.dimension != snapshot.dimension:
            continue
        ids = (
            block.element_tags
            if block.element_tags is not None
            else range(next_id, next_id + len(block.connectivity))
        )
        connectivity = [
            tuple(int(snapshot.node_tags[index]) for index in row)
            for row in block.connectivity
        ]
        blocks.append(
            ElementBlock(
                definition=definition_from_block(block),
                ids=[int(value) for value in ids],
                connectivity=connectivity,
                origins=[origin] * len(connectivity),
            )
        )
        next_id += len(block.connectivity)

    candidate.mesh.replace_element_blocks(blocks)
    candidate.mesh.node_count = len(snapshot.points)
    candidate.mesh.element_count = sum(len(block) for block in blocks)
    candidate.mesh.mesh_dimension = snapshot.dimension
    candidate.mesh.revision = str(
        getattr(snapshot, "fingerprint", "")
        or candidate.mesh.revision
        or "generated"
    )
    candidate.mesh.entity_facets = _derive_entity_facets(candidate)

    candidate.mesh.lifecycle.origin = origin
    candidate.mesh.lifecycle.edit_state = MeshEditState.CLEAN
    candidate.mesh.lifecycle.validity = MeshValidity.CURRENT
    candidate.mesh.lifecycle.geometry_association = (
        GeometryAssociationState.ATTACHED
        if not candidate.mesh.associations.empty
        else GeometryAssociationState.NONE
    )

    if snapshot.qualities is not None and len(snapshot.qualities):
        candidate.mesh.minimum_quality = float(snapshot.qualities.min())
        candidate.mesh.mean_quality = float(snapshot.qualities.mean())
    else:
        candidate.mesh.quality.invalidate()


def _derive_entity_facets(part):
    """Persist CAD-face to oriented element-side associations at mesh time."""
    result = {}
    for label, node_ids in part.mesh.entity_nodes.items():
        if not str(label).startswith("Face-"):
            continue
        nodes = {int(value) for value in node_ids}
        candidates = {
            int(value)
            for value in part.mesh.entity_elements.get(label, ())
        }
        facets = []
        for block in part.mesh.element_blocks:
            category = block.definition.category
            for element_id, connectivity in zip(
                block.ids,
                block.connectivity,
                strict=True,
            ):
                element_id = int(element_id)
                if category in {"Shell Elements", "2D Elements"}:
                    if candidates:
                        if element_id in candidates:
                            facets.append((element_id, "SPOS"))
                    else:
                        element_nodes = {int(value) for value in connectivity}
                        if element_nodes and element_nodes.issubset(nodes):
                            facets.append((element_id, "SPOS"))
                    continue
                for side, indices in element_side_indices(
                    block.definition.topology
                ):
                    corner_nodes = {
                        int(connectivity[index])
                        for index in indices
                        if index < len(connectivity)
                    }
                    if corner_nodes and corner_nodes.issubset(nodes):
                        facets.append((element_id, side))
        result[label] = sorted(set(facets))
    return result
