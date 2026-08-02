from __future__ import annotations

import re

import numpy as np
import pyvista as pv

from opencae.model.core import EntityRef, EntityTarget, region_member_label
from opencae.model.entities.regions import ReferencePoint, Region
from .instance_transform import transform_points, transform_vector
from .vtk_cell_data import cell_array

_LABEL = re.compile(r"^(?:(?P<instance>.+)\.)?(?P<kind>Face|Edge|Vertex|Cell|Node|Element)-(?P<tag>\d+)$", re.I)


def region_samples(project, target, scene, maximum=24):
    entity = _resolve_target(project, target)
    if entity is None:
        return []
    if isinstance(entity, ReferencePoint):
        return _reference_point_samples(project, entity, scene)
    if not isinstance(entity, Region):
        return []
    parent = project.try_resolve(project.index.parent_id.get(entity.id)) if project.index else None
    instances = _owner_instances(project, parent, scene)
    samples = []
    for member in entity.members:
        match = _LABEL.match(region_member_label(project, member))
        if not match:
            continue
        explicit_instance = match.group("instance")
        instance_names = [explicit_instance] if explicit_instance else instances
        if not instance_names:
            instance_names = [next(iter(scene.assembly_snapshots))] if len(scene.assembly_snapshots) == 1 else [None]
        for instance_name in instance_names:
            samples.extend(_member_samples(scene, instance_name, match.group("kind").lower(), int(match.group("tag"))))
    return _thin(samples, maximum)


def _resolve_target(project, target):
    if isinstance(target, EntityTarget):
        return project.try_resolve(target.ref)
    if isinstance(target, EntityRef):
        return project.try_resolve(target)
    if hasattr(target, "id"):
        return target
    text = str(target or "")
    if not text:
        return None
    entity = project.try_resolve(text)
    if entity is not None:
        return entity
    matches = [
        item for item in (
            *project.assembly.node_sets,
            *project.assembly.element_sets,
            *project.assembly.surfaces,
            *project.assembly.reference_points,
        ) if item.name == text
    ]
    return matches[0] if len(matches) == 1 else None


def _owner_instances(project, parent, scene):
    if parent is project.assembly:
        return []
    if parent in project.parts:
        return [
            name for name, instance in scene.assembly_instances.items()
            if instance.part_ref.entity_id == parent.id
        ]
    return []


def _reference_point_samples(project, point, scene):
    parent = project.try_resolve(project.index.parent_id.get(point.id)) if project.index else None
    if parent is project.assembly:
        return [(np.asarray(point.position, dtype=float), None)]
    result = []
    for instance_name in _owner_instances(project, parent, scene):
        instance = scene.instance_for(instance_name)
        result.append((transform_points([point.position], instance)[0], None))
    return result


def _member_samples(scene, instance_name, kind, tag):
    snapshot = scene.snapshot_for(instance_name)
    instance = scene.instance_for(instance_name)
    if kind in {"node", "element"}:
        grid = scene.mesh_grids.get(instance_name) if instance_name else scene.mesh_grid
        if grid is None:
            return []
        if kind == "node":
            try:
                ids = np.asarray(grid.point_data.get("node_id", ()))
            except (AttributeError, RuntimeError, RecursionError):
                return []
        else:
            ids = cell_array(grid, "element_id")
        hits = np.where(ids == tag)[0]
        if not len(hits):
            return []
        try:
            point = grid.points[int(hits[0])] if kind == "node" else grid.get_cell(int(hits[0])).center
        except (AttributeError, RuntimeError, RecursionError, IndexError):
            return []
        return [(np.asarray(point, dtype=float), None)]
    if snapshot is None:
        return []
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
        for patch in patches:
            values.extend(_surface_samples(patch, instance, maximum=2))
        return values
    return []


def _surface_samples(patch, instance, maximum=12):
    points = transform_points(patch.points, instance) if instance else patch.points
    mesh = pv.PolyData(points, patch.faces).compute_normals(cell_normals=True, point_normals=False, consistent_normals=True)
    centers = mesh.cell_centers().points
    normals = np.asarray(mesh.cell_data.get("Normals", np.zeros_like(centers)), dtype=float)
    if instance and len(normals):
        normals = np.asarray([transform_vector(value, instance) for value in normals])
    indices = _even_indices(len(centers), maximum)
    return [(centers[index], _unit(normals[index])) for index in indices]


def _edge_samples(patch, instance, maximum=7):
    points = transform_points(patch.points, instance) if instance else patch.points
    indices = _even_indices(len(points), maximum)
    return [(points[index], None) for index in indices]


def _even_indices(count, maximum):
    if count <= maximum:
        return range(count)
    return sorted(set(int(value) for value in np.linspace(0, count - 1, maximum)))


def _thin(values, maximum):
    if len(values) <= maximum:
        return values
    return [values[index] for index in _even_indices(len(values), maximum)]


def _unit(vector):
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1e-14 else None
