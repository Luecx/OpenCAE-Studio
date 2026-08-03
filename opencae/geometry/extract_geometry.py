from __future__ import annotations

from .display_mesh import generate_display_mesh
from .entity_names import name_entities
from .geometry_bounds import geometry_bounds
from .geometry_patches import edge_patch, surface_patch, vertex_patch
from .snapshots import GeometrySnapshot
from .meshability import classify_cells


def extract_geometry(gmsh, part_id: str, fingerprint: str, size_factor: float = 0.025) -> GeometrySnapshot:
    entities = {dimension: [tag for _, tag in gmsh.model.getEntities(dimension)] for dimension in range(4)}
    bounds = geometry_bounds(gmsh, entities)
    generate_display_mesh(gmsh, bounds, size_factor)
    surfaces = [surface_patch(gmsh, tag) for tag in entities[2]]
    edges = [edge_patch(gmsh, tag) for tag in entities[1]]
    vertices = [vertex_patch(gmsh, tag) for tag in entities[0]]
    name_entities(gmsh, entities)
    adjacency = {tag: list(map(int, gmsh.model.getAdjacencies(2, tag)[0])) for tag in entities[2]}
    snapshot = GeometrySnapshot(
        part_id=part_id,
        surfaces=[patch for patch in surfaces if patch is not None],
        edges=[patch for patch in edges if patch is not None],
        vertices=[patch for patch in vertices if patch is not None],
        entities=entities,
        surface_to_cells=adjacency,
        bounds=bounds,
        fingerprint=fingerprint,
    )
    snapshot.cell_meshability = classify_cells(snapshot)
    return snapshot
