from __future__ import annotations

from .definition import RegionDefinition, RegionSelectionItem
from .hit import ViewportHit
from .operands import (
    GeometryOperand,
    MeshElementOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    ReferencePointOperand,
)
from .types import SelectableKind


def as_region_definition(value) -> RegionDefinition:
    """Normalize region values while keeping object relationships intact."""
    if value is None:
        return RegionDefinition()
    if isinstance(value, RegionDefinition):
        return value
    from opencae.model.entities.regions import Region
    if isinstance(value, Region):
        return RegionDefinition((RegionSelectionItem(NamedRegionOperand(region=value)),))
    raise TypeError(f"Cannot use {type(value).__name__} as a RegionDefinition")


def definition_from_hit(project, hit: ViewportHit, default_owner=None) -> RegionDefinition:
    instance = project.try_resolve(hit.instance_id) if hit.instance_id else None
    if hit.kind == SelectableKind.REFERENCE_POINT:
        point = project.try_resolve(str(hit.entity_id or ""), "ReferencePoint")
        if point is None:
            raise ValueError("Viewport reference point no longer exists")
        operand = ReferencePointOperand(point, instance)
    elif hit.kind == SelectableKind.MESH_NODE:
        owner = _owner(project, hit, default_owner)
        node = owner.mesh.node(int(hit.mesh_id or 0))
        operand = MeshNodeOperand(
            owner,
            node,
            instance,
            _mesh_revision(owner, instance),
        )
    elif hit.kind == SelectableKind.MESH_ELEMENT:
        owner = _owner(project, hit, default_owner)
        element = owner.mesh.element(int(hit.mesh_id or 0))
        operand = MeshElementOperand(
            owner,
            element,
            instance,
            _mesh_revision(owner, instance),
        )
    elif hit.kind == SelectableKind.MESH_FACET:
        owner = _owner(project, hit, default_owner)
        element = owner.mesh.element(int(hit.mesh_id or 0))
        operand = MeshFacetOperand(
            owner,
            element,
            str(hit.local_face or ""),
            instance,
            _mesh_revision(owner, instance),
        )
    elif hit.kind in {
        SelectableKind.GEOMETRY_VERTEX,
        SelectableKind.GEOMETRY_EDGE,
        SelectableKind.GEOMETRY_FACE,
        SelectableKind.GEOMETRY_CELL,
    }:
        owner = _owner(project, hit, default_owner)
        dimension = {
            SelectableKind.GEOMETRY_VERTEX: 0,
            SelectableKind.GEOMETRY_EDGE: 1,
            SelectableKind.GEOMETRY_FACE: 2,
            SelectableKind.GEOMETRY_CELL: 3,
        }[hit.kind]
        operand = GeometryOperand(
            owner,
            dimension,
            int(hit.topology_tag or 0),
            instance,
            _geometry_revision(owner, instance),
        )
    else:
        raise ValueError(f"Unsupported viewport selection kind: {hit.kind}")
    return RegionDefinition(
        (RegionSelectionItem(operand, hit.world_position, hit.label),)
    )


def definition_from_local_labels(owner, values) -> RegionDefinition:
    """Convert viewport labels to direct part-local object selections."""
    from opencae.geometry.labels import parse_entity_label

    items = []
    for value in values or ():
        text = str(value).split(".")[-1]
        parsed = parse_entity_label(text)
        if parsed:
            dimension, tag = parsed
            operand = GeometryOperand(owner, int(dimension), int(tag))
        elif text.casefold().startswith("node-"):
            node = owner.mesh.node(int(text.split("-", 1)[1]))
            operand = MeshNodeOperand(
                owner,
                node,
                mesh_revision=getattr(owner.mesh, "revision", ""),
            )
        elif text.casefold().startswith("element-"):
            element = owner.mesh.element(int(text.split("-", 1)[1]))
            operand = MeshElementOperand(
                owner,
                element,
                mesh_revision=getattr(owner.mesh, "revision", ""),
            )
        else:
            continue
        items.append(RegionSelectionItem(operand, display_label=str(value)))
    return RegionDefinition(tuple(items))


def named_region_definition(region, instance=None) -> RegionDefinition:
    return RegionDefinition(
        (
            RegionSelectionItem(
                NamedRegionOperand(region, instance),
                display_label=_label(instance, region),
            ),
        )
    )


def reference_point_definition(point, instance=None) -> RegionDefinition:
    return RegionDefinition(
        (
            RegionSelectionItem(
                ReferencePointOperand(point, instance),
                display_label=_label(instance, point),
            ),
        )
    )


def _owner(project, hit, default_owner):
    if hit.owner_id:
        owner = project.try_resolve(hit.owner_id)
        if owner is not None:
            return owner
    if hit.instance_id:
        instance = project.try_resolve(hit.instance_id)
        if instance is not None and instance.part is not None:
            return instance.part
    if default_owner is not None:
        return default_owner
    raise ValueError("Viewport selection has no persistent owner")


def _geometry_revision(owner, instance=None):
    part = instance.part if instance is not None and instance.part is not None else owner
    try:
        from opencae.geometry.fingerprint import part_fingerprint
        return part_fingerprint(part, include_mesh=False)
    except (AttributeError, TypeError, ValueError):
        return ""


def _mesh_revision(owner, instance=None):
    part = instance.part if instance is not None and instance.part is not None else owner
    return getattr(getattr(part, "mesh", None), "revision", "")


def _label(instance, entity):
    return f"{instance.name}.{entity.name}" if instance else entity.name
