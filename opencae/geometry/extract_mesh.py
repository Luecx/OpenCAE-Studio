from __future__ import annotations

import logging

import numpy as np

from .entity_membership import extract_entity_membership
from .snapshots import MeshBlock, MeshSnapshot

_LOG = logging.getLogger(__name__)


def extract_mesh(gmsh, part_id: str, dimension: int, fingerprint: str) -> MeshSnapshot:
    node_tags, coords, _ = gmsh.model.mesh.getNodes(-1, -1, False, False)
    node_tags = np.asarray(node_tags, dtype=np.int64)
    points = np.asarray(coords, dtype=float).reshape(-1, 3)
    lookup = {int(tag): index for index, tag in enumerate(node_tags)}
    blocks: list[MeshBlock] = []
    quality_tags: list[int] = []
    element_types, element_tag_blocks, node_blocks = gmsh.model.mesh.getElements(-1, -1)
    for element_type, element_tags, node_block in zip(
        element_types,
        element_tag_blocks,
        node_blocks,
    ):
        name, dim, order, num_nodes, _, num_primary = gmsh.model.mesh.getElementProperties(
            int(element_type)
        )
        tags = np.asarray(element_tags, dtype=np.int64)
        raw = np.asarray(node_block, dtype=np.int64).reshape(-1, num_nodes)
        connectivity = np.asarray(
            [[lookup[int(tag)] for tag in row] for row in raw],
            dtype=np.int64,
        )
        blocks.append(
            MeshBlock(
                gmsh_type=int(element_type),
                name=name,
                dimension=dim,
                order=order,
                primary_nodes=num_primary,
                connectivity=connectivity,
                element_tags=tags,
            )
        )
        # gmsh.model.mesh.generate(3) also creates the boundary surface and edge
        # elements required to describe the CAD topology. Those lower-dimensional
        # elements are useful for entity membership, but they are not FE elements
        # persisted by OpenCAE and some Gmsh quality measures (notably minSICN)
        # do not support 2-node line element type 1. Keep quality statistics aligned
        # with the top-dimensional FE payload only.
        if int(dim) == int(dimension):
            quality_tags.extend(int(tag) for tag in tags)

    qualities = (
        _qualities(gmsh, quality_tags)
        if int(dimension) >= 2
        else None
    )
    entity_nodes, entity_elements = extract_entity_membership(gmsh)
    return MeshSnapshot(
        part_id=part_id,
        node_tags=node_tags,
        points=points,
        blocks=blocks,
        dimension=dimension,
        fingerprint=fingerprint,
        qualities=qualities,
        entity_nodes=entity_nodes,
        entity_elements=entity_elements,
    )


def _qualities(gmsh, tags):
    if not tags:
        return None
    try:
        values = gmsh.model.mesh.getElementQualities(tags, "minSICN")
        return np.asarray(values, dtype=float)
    except Exception as exc:
        _LOG.warning("Could not evaluate mesh quality: %s", exc)
        return None
