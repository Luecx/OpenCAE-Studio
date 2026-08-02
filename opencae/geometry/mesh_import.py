from __future__ import annotations

from pathlib import Path
import re
import numpy as np

from .snapshots import MeshBlock, MeshSnapshot

_TYPE = {
    "T3": (1, "Lines", 1, 2, 1), "B33": (1, "Lines", 1, 2, 1),
    "S3": (2, "Triangles", 1, 3, 2), "MITC3FRT": (2, "Triangles", 1, 3, 2),
    "S4": (3, "Quadrilaterals", 1, 4, 2), "MITC4": (3, "Quadrilaterals", 1, 4, 2),
    "MITC4FRT": (3, "Quadrilaterals", 1, 4, 2), "QSPT": (3, "Quadrilaterals", 1, 4, 2),
    "S6": (9, "Triangles", 2, 3, 2), "MITC6FRT": (9, "Triangles", 2, 3, 2),
    "S8": (16, "Quadrilaterals", 2, 4, 2), "MITC8": (16, "Quadrilaterals", 2, 4, 2),
    "MITC8FRT": (16, "Quadrilaterals", 2, 4, 2),
    "C3D4": (4, "Tetrahedra", 1, 4, 3), "C3D5": (7, "Pyramids", 1, 5, 3),
    "C3D6": (6, "Pentahedra", 1, 6, 3), "C3D8": (5, "Hexahedra", 1, 8, 3), "C3D8R": (5, "Hexahedra", 1, 8, 3),
    "C3D10": (11, "Tetrahedra", 2, 4, 3), "C3D13": (19, "Pyramids", 2, 5, 3),
    "C3D15": (18, "Pentahedra", 2, 6, 3), "C3D20": (17, "Hexahedra", 2, 8, 3), "C3D20R": (17, "Hexahedra", 2, 8, 3),
}


def read_mesh(path, part_id):
    suffix = Path(path).suffix.lower()
    return _read_inp(path, part_id) if suffix in {".inp", ".fem"} else _read_pyvista(path, part_id)


def _read_inp(path, part_id):
    nodes = {}; groups = {}; current = None
    for raw in Path(path).read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("**"): continue
        if line.startswith("*"):
            upper = line.upper(); current = "node" if upper.startswith("*NODE") else "element" if upper.startswith("*ELEMENT") else None
            if current == "element":
                match = re.search(r"TYPE\s*=\s*([^,]+)", upper); element_type = match.group(1).strip() if match else "C3D4"; groups.setdefault(element_type, [])
            continue
        values = [item.strip() for item in line.split(",") if item.strip()]
        if current == "node" and len(values) >= 4: nodes[int(values[0])] = tuple(map(float, values[1:4]))
        elif current == "element" and len(values) >= 2: groups[element_type].append((int(values[0]), tuple(map(int, values[1:]))))
    tags = np.asarray(sorted(nodes), np.int64); lookup = {tag: index for index, tag in enumerate(tags)}; blocks = []
    for name, rows in groups.items():
        if name not in _TYPE: raise ValueError(f"Unsupported element type: {name}")
        gmsh, topology, order, primary, dimension = _TYPE[name]
        blocks.append(MeshBlock(gmsh, topology, dimension, order, primary,
                                np.asarray([[lookup[tag] for tag in row] for _, row in rows], np.int64),
                                np.asarray([eid for eid, _ in rows], np.int64)))
    return MeshSnapshot(part_id, tags, np.asarray([nodes[int(tag)] for tag in tags]), blocks, max((b.dimension for b in blocks), default=0), fingerprint=str(path))


def _read_pyvista(path, part_id):
    import pyvista as pv
    grid = pv.read(path)
    if not hasattr(grid, "cells_dict"): grid = grid.cast_to_unstructured_grid()
    tags = np.asarray(grid.point_data.get("node_id", np.arange(1, grid.n_points + 1)), np.int64); blocks = []
    mapping = {3:(1,"Lines",1,2,1),5:(2,"Triangles",1,3,2),9:(3,"Quadrilaterals",1,4,2),10:(4,"Tetrahedra",1,4,3),12:(5,"Hexahedra",1,8,3),13:(6,"Pentahedra",1,6,3),14:(7,"Pyramids",1,5,3)}
    next_id = 1
    for vtk_type, connectivity in grid.cells_dict.items():
        if int(vtk_type) not in mapping: continue
        gmsh, name, order, primary, dimension = mapping[int(vtk_type)]; count = len(connectivity)
        blocks.append(MeshBlock(gmsh, name, dimension, order, primary, np.asarray(connectivity, np.int64), np.arange(next_id, next_id + count, dtype=np.int64))); next_id += count
    return MeshSnapshot(part_id, tags, np.asarray(grid.points, float), blocks, max((b.dimension for b in blocks), default=0), fingerprint=str(path))
