from __future__ import annotations

_ALGORITHM_2D = {
    "MeshAdapt": 1,
    "Automatic": 2,
    "Delaunay": 5,
    "Frontal-Delaunay": 6,
    "Frontal-Delaunay for Quads": 8,
}
_ALGORITHM_3D = {"Delaunay": 1, "Frontal": 4, "HXT": 10}


def apply_general_options(gmsh, part) -> None:
    settings = part.mesh.settings
    gmsh.option.setNumber("Mesh.Algorithm", _ALGORITHM_2D.get(settings.algorithm_2d, 6))
    gmsh.option.setNumber("Mesh.Algorithm3D", _ALGORITHM_3D.get(settings.algorithm_3d, 10))
    gmsh.option.setNumber("Mesh.RecombineAll", 1 if settings.recombine_all else 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    if settings.num_threads > 0:
        gmsh.option.setNumber("General.NumThreads", settings.num_threads)


def default_seed(part):
    return next((seed for seed in part.mesh.seeds if seed.seed_type == "Default"), None)


def apply_default_seed(gmsh, part) -> float:
    seed = default_seed(part)
    if seed is None:
        size = _automatic_size(gmsh)
    else:
        size = max(float(seed.size), 1.0e-12)
    minimum_factor = float((seed.metadata if seed else {}).get("minimum", 0.1))
    gmsh.option.setNumber("Mesh.MeshSizeMax", size)
    gmsh.option.setNumber("Mesh.MeshSizeMin", size * max(minimum_factor, 1.0e-4))
    return size


def _automatic_size(gmsh) -> float:
    entities = gmsh.model.getEntities(3) or gmsh.model.getEntities(2) or gmsh.model.getEntities(1)
    if not entities:
        return 1.0
    boxes = [gmsh.model.getBoundingBox(dim, tag) for dim, tag in entities]
    spans = [max(box[i+3] for box in boxes) - min(box[i] for box in boxes) for i in range(3)]
    return max(max(spans) / 30.0, 1.0e-6)
