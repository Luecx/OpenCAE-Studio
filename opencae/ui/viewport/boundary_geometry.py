from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.regions import ReferencePoint, Region
from opencae.model.selection import (
    GeometryOperand, MeshElementOperand, MeshFacetOperand, MeshNodeOperand,
    NamedRegionOperand, ReferencePointOperand, RegionDefinition, RegionSelectionItem,
    WholeModelOperand,
)
from .instance_transform import transform_points, transform_vector
from .vtk_cell_data import cell_array


def region_samples(project, target, scene, maximum=24):
    definition = _definition(target)
    if definition is None:
        return []
    samples = []
    _sample_definition(project, definition, scene, samples, set(), None)
    return _thin(samples, maximum)


def _definition(target):
    if isinstance(target, RegionDefinition):
        return target
    if isinstance(target, Region):
        return target.definition
    if isinstance(target, ReferencePoint):
        return RegionDefinition((RegionSelectionItem(ReferencePointOperand(reference_point_ref=target.ref())),))
    if isinstance(target, RegionSelectionItem):
        return RegionDefinition((target,))
    if hasattr(target, "kind"):
        return RegionDefinition((RegionSelectionItem(target),))
    return None


def _sample_definition(project, definition, scene, samples, stack, inherited_instance):
    for item in RegionDefinition.from_values(definition).items:
        operand = item.operand
        if isinstance(operand, NamedRegionOperand):
            region = project.try_resolve(operand.region_ref)
            if region is None or region.id in stack:
                continue
            instance_id = _ref_id(operand.instance_ref) or inherited_instance
            _sample_definition(project, region.definition, scene, samples, {*stack, region.id}, instance_id)
            continue
        if isinstance(operand, ReferencePointOperand):
            point = project.try_resolve(operand.reference_point_ref)
            if point is None:
                continue
            for instance_id in _occurrence_ids(project, point, operand.instance_ref, inherited_instance, scene):
                instance = scene.instance_for(instance_id)
                position = transform_points([point.position], instance)[0] if instance else np.asarray(point.position, float)
                samples.append((position, None))
            continue
        if isinstance(operand, WholeModelOperand):
            continue
        owner = project.try_resolve(getattr(operand, "owner_ref", None))
        occurrence_ids = _occurrence_ids(project, owner, getattr(operand, "instance_ref", None), inherited_instance, scene)
        for occurrence_id in occurrence_ids:
            if isinstance(operand, GeometryOperand):
                samples.extend(_geometry_samples(scene, occurrence_id, operand.dimension, operand.tag))
            elif isinstance(operand, MeshNodeOperand):
                samples.extend(_mesh_samples(scene, occurrence_id, "node", operand.node_id))
            elif isinstance(operand, (MeshElementOperand, MeshFacetOperand)):
                samples.extend(_mesh_samples(scene, occurrence_id, "element", operand.element_id))


def _occurrence_ids(project, owner, explicit_ref, inherited_instance, scene):
    explicit_id = _ref_id(explicit_ref) or inherited_instance
    if explicit_id:
        return [explicit_id]
    from opencae.model.entities.assembly import Instance
    from opencae.model.entities.parts import Part
    if isinstance(owner, Instance):
        return [owner.id]
    if isinstance(owner, Part):
        if scene.part_id == owner.id and not scene.assembly_instances:
            return [None]
        return [instance.id for instance in scene.assembly_instances.values() if instance.part_ref.entity_id == owner.id]
    parent_id = project.index.parent_id.get(getattr(owner, "id", "")) if project.index else None
    parent = project.try_resolve(parent_id) if parent_id else None
    if parent is project.assembly:
        return [None]
    if isinstance(parent, Part):
        return [instance.id for instance in scene.assembly_instances.values() if instance.part_ref.entity_id == parent.id]
    return [None]


def _geometry_samples(scene, instance_id, dimension, tag):
    snapshot = scene.snapshot_for(instance_id)
    instance = scene.instance_for(instance_id)
    if snapshot is None:
        return []
    if dimension == 0:
        patch = next((item for item in snapshot.vertices if item.tag == tag), None)
        if patch is None:
            return []
        point = transform_points([patch.point], instance)[0] if instance else np.asarray(patch.point, float)
        return [(point, None)]
    if dimension == 1:
        patch = next((item for item in snapshot.edges if item.tag == tag), None)
        return _edge_samples(patch, instance) if patch else []
    if dimension == 2:
        patch = next((item for item in snapshot.surfaces if item.tag == tag), None)
        return _surface_samples(patch, instance) if patch else []
    patches = [item for item in snapshot.surfaces if tag in snapshot.surface_to_cells.get(item.tag, ())]
    result = []
    for patch in patches:
        result.extend(_surface_samples(patch, instance, maximum=2))
    return result


def _mesh_samples(scene, instance_id, kind, tag):
    grid = scene.mesh_grids.get(instance_id) if instance_id else scene.mesh_grid
    if grid is None:
        return []
    if kind == "node":
        try:
            ids = np.asarray(grid.point_data.get("node_id", ()))
        except (AttributeError, RuntimeError, RecursionError):
            return []
        hits = np.where(ids == int(tag))[0]
        return [(np.asarray(grid.points[int(hits[0])], float), None)] if len(hits) else []
    ids = cell_array(grid, "element_id")
    hits = np.where(ids == int(tag))[0]
    if not len(hits):
        return []
    try:
        return [(np.asarray(grid.get_cell(int(hits[0])).center, float), None)]
    except (AttributeError, RuntimeError, RecursionError, IndexError):
        return []


def _surface_samples(patch, instance, maximum=12):
    points = transform_points(patch.points, instance) if instance else patch.points
    mesh = pv.PolyData(points, patch.faces).compute_normals(cell_normals=True, point_normals=False, consistent_normals=True)
    centers = mesh.cell_centers().points
    normals = np.asarray(mesh.cell_data.get("Normals", np.zeros_like(centers)), dtype=float)
    if instance and len(normals):
        normals = np.asarray([transform_vector(value, instance) for value in normals])
    return [(centers[index], _unit(normals[index])) for index in _even_indices(len(centers), maximum)]


def _edge_samples(patch, instance, maximum=7):
    points = transform_points(patch.points, instance) if instance else patch.points
    return [(points[index], None) for index in _even_indices(len(points), maximum)]


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


def _ref_id(ref):
    return ref.entity_id if ref else ""
