from __future__ import annotations

import numpy as np

from .snapshots import MeshBlock, MeshSnapshot


def snapshot_from_part(part):
    mesh = part.mesh
    if not mesh.nodes.ids or not mesh.element_blocks: return None
    tags = np.asarray(mesh.nodes.ids, dtype=np.int64); points = np.asarray(mesh.nodes.coordinates, dtype=float)
    lookup = {int(tag): index for index, tag in enumerate(tags)}; blocks = []
    for block in mesh.element_blocks:
        connectivity = np.asarray([[lookup[int(tag)] for tag in row] for row in block.connectivity], dtype=np.int64)
        definition = block.definition; dimension = _dimension(definition.category)
        blocks.append(MeshBlock(
            gmsh_type=int(getattr(definition, "gmsh_type", 0) or 0), name=definition.topology,
            dimension=dimension, order=2 if definition.order == "Quadratic" else 1,
            primary_nodes=_primary(definition.topology, connectivity.shape[1]), connectivity=connectivity,
            element_tags=np.asarray(block.ids, dtype=np.int64),
        ))
    return MeshSnapshot(part.id, tags, points, blocks, mesh.mesh_dimension or max((item.dimension for item in blocks), default=0),
                        fingerprint="orphan", entity_nodes=dict(mesh.entity_nodes), entity_elements=dict(mesh.entity_elements))


def _dimension(category):
    return 1 if category == "Line Elements" else 2 if category in {"Shell Elements", "2D Elements"} else 3


def _primary(topology, count):
    text = topology.lower()
    if "line" in text: return 2
    if "triangle" in text: return 3
    if "quadrilateral" in text: return 4
    if "tetra" in text: return 4
    if "penta" in text or "wedge" in text: return 6
    if "pyramid" in text: return 5
    if "hexa" in text: return 8
    return count
