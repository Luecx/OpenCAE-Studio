import numpy as np

from .snapshots import EdgePatch, SurfacePatch, VertexPatch


def surface_patch(gmsh, tag: int) -> SurfacePatch | None:
    node_tags, coords, _ = gmsh.model.mesh.getNodes(2, tag, True, False)
    if len(node_tags) == 0:
        return None
    points = np.asarray(coords, dtype=float).reshape(-1, 3)
    lookup = {int(node): index for index, node in enumerate(node_tags)}
    faces = _surface_faces(gmsh, tag, lookup)
    if not faces:
        return None
    return SurfacePatch(tag=tag, points=points, faces=np.asarray(faces, dtype=np.int64))


def edge_patch(gmsh, tag: int) -> EdgePatch | None:
    node_tags, coords, _ = gmsh.model.mesh.getNodes(1, tag, True, False)
    if len(node_tags) == 0:
        return None
    points = np.asarray(coords, dtype=float).reshape(-1, 3)
    lookup = {int(node): index for index, node in enumerate(node_tags)}
    lines = _edge_lines(gmsh, tag, lookup)
    if not lines:
        return None
    return EdgePatch(tag=tag, points=points, lines=np.asarray(lines, dtype=np.int64))


def _surface_faces(gmsh, tag, lookup):
    faces: list[int] = []
    types, _, node_blocks = gmsh.model.mesh.getElements(2, tag)
    for element_type, node_block in zip(types, node_blocks):
        _, dim, _, num_nodes, _, primary = gmsh.model.mesh.getElementProperties(int(element_type))
        if dim != 2:
            continue
        rows = np.asarray(node_block, dtype=np.int64).reshape(-1, num_nodes)[:, :primary]
        for row in rows:
            local = [lookup.get(int(node)) for node in row]
            if any(index is None for index in local):
                continue
            _append_face(faces, local)
    return faces


def _append_face(faces, local):
    if len(local) in (3, 4):
        faces.extend((len(local), *local))
        return
    for index in range(1, len(local) - 1):
        faces.extend((3, local[0], local[index], local[index + 1]))


def _edge_lines(gmsh, tag, lookup):
    lines: list[int] = []
    types, _, node_blocks = gmsh.model.mesh.getElements(1, tag)
    for element_type, node_block in zip(types, node_blocks):
        _, dim, _, num_nodes, _, primary = gmsh.model.mesh.getElementProperties(int(element_type))
        if dim != 1:
            continue
        rows = np.asarray(node_block, dtype=np.int64).reshape(-1, num_nodes)[:, :primary]
        for row in rows:
            local = [lookup.get(int(node)) for node in row]
            if len(local) < 2 or any(index is None for index in local):
                continue
            for index in range(len(local) - 1):
                lines.extend((2, local[index], local[index + 1]))
    return lines


def vertex_patch(gmsh, tag: int) -> VertexPatch | None:
    try:
        point = np.asarray(gmsh.model.getValue(0, tag, []), dtype=float).reshape(3)
        return VertexPatch(tag=tag, point=point)
    except Exception:
        return None
