import numpy as np


def generate_display_mesh(gmsh, bounds, size_factor: float) -> None:
    if bounds is None:
        return
    diagonal = float(np.linalg.norm(np.array(bounds[3:]) - np.array(bounds[:3])))
    size = max(diagonal * max(size_factor, 0.001), 1.0e-8)
    gmsh.option.setNumber("Mesh.MeshSizeMin", size)
    gmsh.option.setNumber("Mesh.MeshSizeMax", size)
    gmsh.option.setNumber("Mesh.ElementOrder", 1)
    if gmsh.model.getEntities(2):
        gmsh.model.mesh.generate(2)
    elif gmsh.model.getEntities(1):
        gmsh.model.mesh.generate(1)
