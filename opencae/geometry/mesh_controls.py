from __future__ import annotations

from .labels import parse_labels


def apply_mesh_controls(gmsh, part) -> None:
    for control in part.mesh.controls:
        if not control.enabled:
            continue
        dim = {"Edge": 1, "Face": 2, "Cell": 3}.get(control.scope, 3)
        available = {tag for _, tag in gmsh.model.getEntities(dim)}
        tags = [tag for _, tag in parse_labels(control.targets, dim) if tag in available]
        if not tags:
            tags = list(available)
        if control.technique in {"Structured", "Transfinite"}:
            _transfinite(gmsh, dim, tags)
        if control.topology in {"Quadrilateral", "Hexahedral"} or control.technique == "Recombine":
            _recombine_boundaries(gmsh, dim, tags)


def _transfinite(gmsh, dim, tags):
    if dim == 1:
        return
    if dim == 2:
        for tag in tags:
            gmsh.model.mesh.setTransfiniteSurface(tag)
        return
    for tag in tags:
        boundaries = gmsh.model.getBoundary([(3, tag)], oriented=False, recursive=False)
        for _, surface in boundaries:
            try:
                gmsh.model.mesh.setTransfiniteSurface(surface)
            except Exception:
                pass
        gmsh.model.mesh.setTransfiniteVolume(tag)


def _recombine_boundaries(gmsh, dim, tags):
    surfaces = tags if dim == 2 else []
    if dim == 3:
        for tag in tags:
            surfaces.extend(surface for d, surface in gmsh.model.getBoundary([(3, tag)], oriented=False, recursive=False) if d == 2)
    for tag in set(surfaces):
        gmsh.model.mesh.setRecombine(2, tag)
