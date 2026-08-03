from __future__ import annotations

from opencae.model.selection import local_geometry_tags


def apply_edge_seeds(gmsh, part) -> None:
    available = {tag for _, tag in gmsh.model.getEntities(1)}
    for seed in part.mesh.seeds:
        if seed.seed_type != "Edge" or not seed.enabled:
            continue
        tags = sorted(local_geometry_tags(part, seed.target, 1) & available)
        for tag in tags:
            divisions = _divisions(gmsh, seed, tag)
            mesh_type, coefficient = _distribution(seed)
            gmsh.model.mesh.setTransfiniteCurve(tag, divisions + 1, mesh_type, coefficient)


def _divisions(gmsh, seed, tag: int) -> int:
    if seed.method == "Number of divisions" and seed.divisions > 0:
        return seed.divisions
    length = float(gmsh.model.occ.getMass(1, tag))
    return max(1, int(round(length / max(seed.size, 1.0e-12))))


def _distribution(seed):
    factor = max(float(seed.bias_factor), 1.0)
    if seed.bias == "Single": return "Progression", factor
    if seed.bias == "Double": return "Bump", factor
    return "Progression", 1.0
