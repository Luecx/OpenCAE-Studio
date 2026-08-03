from __future__ import annotations

from opencae.model.core.reference import EntityRef
from .definition import RegionDefinition, RegionSelectionItem
from .hit import ViewportHit
from .operands import (
    GeometryOperand, MeshElementOperand, MeshFacetOperand, MeshNodeOperand, NamedRegionOperand,
    ReferencePointOperand, WholeModelOperand,
)
from .types import SelectableKind


def as_region_definition(value) -> RegionDefinition:
    """Normalize current runtime values without accepting legacy target wrappers."""
    if value is None: return RegionDefinition()
    if isinstance(value, RegionDefinition): return value
    if isinstance(value, EntityRef): return RegionDefinition((RegionSelectionItem(NamedRegionOperand(value)),))
    raise TypeError(f"Cannot use {type(value).__name__} as a RegionDefinition")


def definition_from_hit(project, hit: ViewportHit, default_owner=None) -> RegionDefinition:
    instance_ref = EntityRef(hit.instance_id, "Instance") if hit.instance_id else None
    if hit.kind == SelectableKind.REFERENCE_POINT:
        # Assembly reference points have no Part owner.  Their own immutable
        # entity ID plus the optional instance occurrence is sufficient.
        operand = ReferencePointOperand(EntityRef(str(hit.entity_id or ""), "ReferencePoint"), instance_ref)
    elif hit.kind == SelectableKind.MESH_NODE:
        owner_ref = _owner_ref(project, hit, default_owner)
        operand = MeshNodeOperand(owner_ref, int(hit.mesh_id or 0), instance_ref, _mesh_revision(project, owner_ref, instance_ref))
    elif hit.kind == SelectableKind.MESH_ELEMENT:
        owner_ref = _owner_ref(project, hit, default_owner)
        operand = MeshElementOperand(owner_ref, int(hit.mesh_id or 0), instance_ref, _mesh_revision(project, owner_ref, instance_ref))
    elif hit.kind == SelectableKind.MESH_FACET:
        owner_ref = _owner_ref(project, hit, default_owner)
        operand = MeshFacetOperand(
            owner_ref, int(hit.mesh_id or 0), str(hit.local_face or ""),
            instance_ref, _mesh_revision(project, owner_ref, instance_ref),
        )
    elif hit.kind in {SelectableKind.GEOMETRY_VERTEX, SelectableKind.GEOMETRY_EDGE, SelectableKind.GEOMETRY_FACE, SelectableKind.GEOMETRY_CELL}:
        owner_ref = _owner_ref(project, hit, default_owner)
        dimension = {SelectableKind.GEOMETRY_VERTEX:0, SelectableKind.GEOMETRY_EDGE:1, SelectableKind.GEOMETRY_FACE:2, SelectableKind.GEOMETRY_CELL:3}[hit.kind]
        operand = GeometryOperand(owner_ref, dimension, int(hit.topology_tag or 0), instance_ref, _geometry_revision(project, owner_ref, instance_ref))
    else:
        raise ValueError(f"Unsupported viewport selection kind: {hit.kind}")
    return RegionDefinition((RegionSelectionItem(operand, hit.world_position, hit.label),))



def definition_from_local_labels(owner, values) -> RegionDefinition:
    """Convert legacy viewport labels to a typed part-local definition."""
    from opencae.geometry.labels import parse_entity_label
    owner_ref = EntityRef.of(owner, type(owner).__name__)
    items = []
    for value in values or ():
        text = str(value).split(".")[-1]
        parsed = parse_entity_label(text)
        if parsed:
            dimension, tag = parsed
            operand = GeometryOperand(owner_ref, int(dimension), int(tag))
        elif text.casefold().startswith("node-"):
            operand = MeshNodeOperand(owner_ref, int(text.split("-", 1)[1]), mesh_revision=getattr(owner.mesh, "revision", ""))
        elif text.casefold().startswith("element-"):
            operand = MeshElementOperand(owner_ref, int(text.split("-", 1)[1]), mesh_revision=getattr(owner.mesh, "revision", ""))
        else:
            continue
        items.append(RegionSelectionItem(operand, display_label=str(value)))
    return RegionDefinition(tuple(items))

def named_region_definition(region, instance=None) -> RegionDefinition:
    return RegionDefinition((RegionSelectionItem(NamedRegionOperand(EntityRef.of(region, "Region"), EntityRef.of(instance, "Instance") if instance else None), display_label=_label(instance, region)),))


def reference_point_definition(point, instance=None) -> RegionDefinition:
    return RegionDefinition((RegionSelectionItem(ReferencePointOperand(EntityRef.of(point, "ReferencePoint"), EntityRef.of(instance, "Instance") if instance else None), display_label=_label(instance, point)),))


def _owner_ref(project, hit, default_owner):
    if hit.owner_id: return EntityRef(hit.owner_id)
    if hit.instance_id:
        instance = project.try_resolve(hit.instance_id)
        part = project.try_resolve(instance.part_ref) if instance else None
        if part: return EntityRef.of(part, "Part")
    if default_owner is not None: return EntityRef.of(default_owner, type(default_owner).__name__)
    raise ValueError("Viewport selection has no persistent owner")



def _geometry_revision(project, owner_ref, instance_ref):
    owner = project.try_resolve(instance_ref or owner_ref)
    if owner is not None and hasattr(owner, "part_ref"):
        owner = project.try_resolve(owner.part_ref)
    if owner is None:
        return ""
    try:
        from opencae.geometry.fingerprint import part_fingerprint
        return part_fingerprint(owner, include_mesh=False)
    except (AttributeError, TypeError, ValueError):
        return ""

def _mesh_revision(project, owner_ref, instance_ref):
    owner = project.try_resolve(instance_ref or owner_ref)
    if owner is not None and hasattr(owner, "part_ref"): owner = project.try_resolve(owner.part_ref)
    return getattr(getattr(owner, "mesh", None), "revision", "")


def _label(instance, entity): return f"{instance.name}.{entity.name}" if instance else entity.name
