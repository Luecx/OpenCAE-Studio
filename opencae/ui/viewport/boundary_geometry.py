from __future__ import annotations

import re
import numpy as np
import pyvista as pv

from .instance_transform import transform_points, transform_vector

_LABEL = re.compile(r"^(?:(?P<instance>[^.]+)\.)?(?P<kind>Face|Edge|Vertex|Cell|Node|Element)-(?P<tag>\d+)$", re.I)


def region_samples(project, region_name, scene, maximum=24):
    region = next((item for item in (*project.assembly.node_sets, *project.assembly.element_sets, *project.assembly.surfaces) if item.name == region_name), None)
    if region is None: return []
    samples = []
    for member in region.members:
        match = _LABEL.match(str(member))
        if not match: continue
        instance_name = match.group("instance")
        if not instance_name and len(scene.assembly_snapshots) == 1:
            instance_name = next(iter(scene.assembly_snapshots))
        samples.extend(_member_samples(scene, instance_name, match.group("kind").lower(), int(match.group("tag"))))
    return _thin(samples, maximum)


def _member_samples(scene, instance_name, kind, tag):
    snapshot = scene.snapshot_for(instance_name); instance = scene.instance_for(instance_name)
    if kind in {"node", "element"}:
        grid = scene.mesh_grids.get(instance_name) if instance_name else scene.mesh_grid
        if grid is None: return []
        data = grid.point_data if kind == "node" else grid.cell_data; key = "node_id" if kind == "node" else "element_id"
        ids = np.asarray(data.get(key, ())); hits = np.where(ids == tag)[0]
        if not len(hits): return []
        point = grid.points[int(hits[0])] if kind == "node" else grid.get_cell(int(hits[0])).center
        return [(point, None)]
    if snapshot is None: return []
    if kind == "face":
        patch = next((item for item in snapshot.surfaces if item.tag == tag), None)
        return _surface_samples(patch, instance) if patch else []
    if kind == "edge":
        patch = next((item for item in snapshot.edges if item.tag == tag), None)
        return _edge_samples(patch, instance) if patch else []
    if kind == "vertex":
        patch = next((item for item in snapshot.vertices if item.tag == tag), None)
        point = transform_points([patch.point], instance)[0] if patch and instance else (patch.point if patch else None)
        return [(point, None)] if point is not None else []
    if kind == "cell":
        patches = [item for item in snapshot.surfaces if tag in snapshot.surface_to_cells.get(item.tag, [])]
        values = []
        for patch in patches: values.extend(_surface_samples(patch, instance, maximum=2))
        return values
    return []


def _surface_samples(patch, instance, maximum=12):
    points = transform_points(patch.points, instance) if instance else patch.points
    mesh = pv.PolyData(points, patch.faces).compute_normals(cell_normals=True, point_normals=False, consistent_normals=True)
    centers = mesh.cell_centers().points
    normals = np.asarray(mesh.cell_data.get("Normals", np.zeros_like(centers)), dtype=float)
    if instance and len(normals): normals = np.asarray([transform_vector(value, instance) for value in normals])
    indices = _even_indices(len(centers), maximum)
    return [(centers[index], _unit(normals[index])) for index in indices]


def _edge_samples(patch, instance, maximum=7):
    points = transform_points(patch.points, instance) if instance else patch.points
    indices = _even_indices(len(points), maximum)
    return [(points[index], None) for index in indices]


def _even_indices(count, maximum):
    if count <= maximum: return range(count)
    return sorted(set(int(value) for value in np.linspace(0, count - 1, maximum)))


def _thin(values, maximum):
    if len(values) <= maximum: return values
    return [values[index] for index in _even_indices(len(values), maximum)]


def _unit(vector):
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1e-14 else None
