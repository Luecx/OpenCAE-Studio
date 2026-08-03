from __future__ import annotations

from collections.abc import Iterable

from .reference import (
    EntityRef,
    EntityTarget,
    InstanceEntityTarget,
    MeshElementTarget,
    MeshNodeTarget,
    RegionMemberTarget,
    TargetKind,
    entity_target,
    instance_entity_target,
    target_label,
)
from .region_member import RegionMemberKind, member_from_selection


def assembly_target_options(project, destination_kind: TargetKind | str) -> list[tuple[str, object]]:
    """Return rename-safe target choices including Part-owned entities per Instance."""
    kind = TargetKind.coerce(destination_kind)
    result: list[tuple[str, object]] = []

    for entity in _assembly_entities(project, kind):
        target = entity_target(entity, _natural_kind(entity))
        result.append((entity.name, target))

    for instance in project.assembly.instances:
        if instance.suppressed:
            continue
        part = project.try_resolve(instance.part_ref)
        if part is None:
            continue
        for entity in _part_entities(part, kind):
            target = instance_entity_target(instance, entity, _natural_kind(entity))
            result.append((f"{instance.name}.{entity.name}", target))
    return result


def part_target_options(part, destination_kind: TargetKind | str) -> list[tuple[str, object]]:
    kind = TargetKind.coerce(destination_kind)
    return [(entity.name, entity_target(entity, _natural_kind(entity))) for entity in _part_entities(part, kind)]


def target_from_selection(project, selection: dict, destination_kind: TargetKind | str, default_owner=None):
    """Convert one viewport hit into a persistent target for the requested context."""
    destination = TargetKind.coerce(destination_kind)
    member = member_from_selection(project, selection, default_owner)
    if member is None:
        return None

    if member.kind == RegionMemberKind.REFERENCE_POINT:
        point = project.try_resolve(member.entity_ref) if member.entity_ref else None
        owner = project.try_resolve(member.owner_ref) if member.owner_ref.entity_id else None
        if point is None:
            return None
        from opencae.model.entities.assembly import Instance
        if isinstance(owner, Instance):
            return InstanceEntityTarget(
                TargetKind.REFERENCE_POINT,
                EntityRef.of(owner, "Instance"),
                EntityRef.of(point, "ReferencePoint"),
            )
        return entity_target(point, TargetKind.REFERENCE_POINT)

    if member.kind == RegionMemberKind.NODE and destination == TargetKind.NODE_SET:
        return MeshNodeTarget(member.owner_ref, int(member.tag))
    if member.kind == RegionMemberKind.ELEMENT and destination == TargetKind.ELEMENT_SET:
        return MeshElementTarget(member.owner_ref, int(member.tag))

    allowed_members = {
        TargetKind.NODE_SET: {
            RegionMemberKind.VERTEX,
            RegionMemberKind.EDGE,
            RegionMemberKind.FACE,
            RegionMemberKind.NODE,
        },
        TargetKind.SURFACE: {RegionMemberKind.FACE},
        TargetKind.ELEMENT_SET: {
            RegionMemberKind.EDGE,
            RegionMemberKind.FACE,
            RegionMemberKind.CELL,
            RegionMemberKind.ELEMENT,
        },
    }
    if member.kind not in allowed_members.get(destination, set()):
        return None
    return RegionMemberTarget(destination, member)


def target_option(project, target) -> tuple[str, object]:
    return target_label(project, target), target


def target_matches_kind(target, allowed: Iterable[TargetKind | str]) -> bool:
    kinds = {TargetKind.coerce(item) for item in allowed}
    return getattr(target, "kind", TargetKind.UNKNOWN) in kinds


def _assembly_entities(project, kind: TargetKind):
    if kind == TargetKind.NODE_SET:
        return (*project.assembly.node_sets, *project.assembly.reference_points)
    if kind == TargetKind.ELEMENT_SET:
        return tuple(project.assembly.element_sets)
    if kind == TargetKind.SURFACE:
        return tuple(project.assembly.surfaces)
    if kind == TargetKind.REFERENCE_POINT:
        return tuple(project.assembly.reference_points)
    return ()


def _part_entities(part, kind: TargetKind):
    if kind == TargetKind.NODE_SET:
        return (*part.node_sets, *part.reference_points)
    if kind == TargetKind.ELEMENT_SET:
        return tuple(part.element_sets)
    if kind == TargetKind.SURFACE:
        return tuple(part.surfaces)
    if kind == TargetKind.REFERENCE_POINT:
        return tuple(part.reference_points)
    return ()


def _natural_kind(entity) -> TargetKind:
    region_type = str(getattr(entity, "region_type", ""))
    if region_type == "Node Set":
        return TargetKind.NODE_SET
    if region_type == "Element Set":
        return TargetKind.ELEMENT_SET
    if region_type == "Surface":
        return TargetKind.SURFACE
    from opencae.model.entities.regions import ReferencePoint
    return TargetKind.REFERENCE_POINT if isinstance(entity, ReferencePoint) else TargetKind.UNKNOWN
