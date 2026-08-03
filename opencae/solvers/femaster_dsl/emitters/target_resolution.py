from __future__ import annotations

from opencae.model.core import (
    EntityTarget,
    InstanceEntityTarget,
    MeshElementTarget,
    MeshNodeTarget,
    RegionMemberKind,
    RegionMemberRef,
    RegionMemberTarget,
    TargetKind,
    region_member_local_label,
)

from ..command import command
from .region_resolution import resolve_members, surface_entries


def target_name(target, writer, context, *, preferred_instance=None):
    if isinstance(target, EntityTarget):
        entity = context.resolve(target.ref)
        if entity is None:
            legacy = target.ref.legacy_name
            if legacy:
                return context.options.get("region_aliases", {}).get(legacy, legacy)
            raise ValueError("Referenced target no longer exists")
        if preferred_instance is not None:
            exact = context.options.get("instance_region_aliases", {}).get((preferred_instance.id, entity.id))
            if exact:
                return exact
        return entity_target_name(entity, target.kind.value, writer, context)
    if isinstance(target, InstanceEntityTarget):
        instance = context.resolve(target.instance_ref)
        entity = context.resolve(target.entity_ref)
        if instance is None or entity is None:
            raise ValueError("Instance target no longer exists")
        exact = context.options.get("instance_region_aliases", {}).get((instance.id, entity.id))
        if exact:
            return exact
        raise ValueError(f"No exported target exists for '{instance.name}.{entity.name}'")
    if isinstance(target, RegionMemberTarget):
        return direct_member_target_name(target, writer, context, preferred_instance=preferred_instance)
    if isinstance(target, MeshElementTarget):
        member = RegionMemberRef(RegionMemberKind.ELEMENT, target.owner_ref, target.element_id)
        return direct_member_target_name(RegionMemberTarget(TargetKind.ELEMENT_SET, member), writer, context, preferred_instance=preferred_instance)
    if isinstance(target, MeshNodeTarget):
        member = RegionMemberRef(RegionMemberKind.NODE, target.owner_ref, target.node_id)
        return direct_member_target_name(RegionMemberTarget(TargetKind.NODE_SET, member), writer, context, preferred_instance=preferred_instance)
    raise TypeError(f"Unsupported entity target type {type(target).__name__}")


def entity_target_name(entity, kind, writer, context):
    aliases = context.options.get("entity_aliases", {})
    if entity.id in aliases:
        return aliases[entity.id]
    aliases = context.options.get("part_region_aliases", {}).get(entity.id, ())
    if len(aliases) == 1:
        return aliases[0]
    if len(aliases) > 1:
        return _merged_target(entity, kind, writer, context)
    raise ValueError(f"No exported target exists for {type(entity).__name__} '{entity.name}'")


def direct_member_target_name(target, writer, context, *, preferred_instance=None):
    member = target.member
    owner = context.resolve(member.owner_ref)
    if owner is None:
        raise ValueError("Direct target owner no longer exists")
    exported = context.options.get("exported_instances", ())
    candidates = []
    for part, instance, node_map, element_map in exported:
        if preferred_instance is not None and getattr(instance, "id", None) != preferred_instance.id:
            continue
        if owner.id in {part.id, getattr(instance, "id", None)}:
            candidates.append((part, instance, node_map, element_map))
    if not candidates:
        raise ValueError("Direct target owner is not part of the exported assembly")

    cache = context.options.setdefault("direct_target_aliases", {})
    key = (target.kind.value, member.owner_ref.entity_id, member.kind.value, str(member.tag), getattr(preferred_instance, "id", ""))
    if key in cache:
        return cache[key]
    label = region_member_local_label(context.project, member)
    name = context.names.register(("direct-target", *key), f"__{target.kind.value}_{label}")

    if target.kind == TargetKind.NODE_SET:
        values = set()
        for part, instance, node_map, _element_map in candidates:
            owner_id = instance.id if instance else part.id
            direct = context.options.get("instance_reference_nodes", {}).get(owner_id, {})
            found, _missing = resolve_members([label], node_map, part.mesh.entity_nodes, direct)
            values.update(found)
        if not values:
            raise ValueError(f"Direct target '{label}' contains no exported nodes")
        command(writer, "NSET", [(value,) for value in sorted(values)], NSET=name)
    elif target.kind == TargetKind.ELEMENT_SET:
        values = set()
        from opencae.geometry.element_targets import resolve_target_ids
        for part, _instance, _node_map, element_map in candidates:
            values.update(element_map[value] for value in resolve_target_ids(part, [member]) if value in element_map)
        if not values:
            raise ValueError(f"Direct target '{label}' contains no exported elements")
        command(writer, "ELSET", [(value,) for value in sorted(values)], ELSET=name)
    elif target.kind == TargetKind.SURFACE:
        entries = []
        for part, _instance, node_map, element_map in candidates:
            found, _missing = surface_entries(part, [label], node_map, element_map)
            entries.extend(found)
        if not entries:
            raise ValueError(f"Direct target '{label}' contains no exported surface facets")
        start = int(context.options.get("next_surface_id", 1))
        rows = [(start + index, element_id, side) for index, (element_id, side) in enumerate(entries)]
        command(writer, "SURFACE", rows, NAME=name)
        context.options["next_surface_id"] = start + len(rows)
    else:
        raise ValueError(f"Unsupported direct target kind {target.kind.value}")
    cache[key] = name
    return name


def _merged_target(entity, kind, writer, context):
    cache = context.options.setdefault("merged_region_aliases", {})
    if entity.id in cache:
        return cache[entity.id]
    data = context.options.get("part_region_data", {}).get(entity.id, {})
    values = data.get("values", [])
    command_name = data.get("command") or ("NSET" if str(kind) in {"Node Set", "Reference Point"} else "ELSET")
    name = context.names.register(("merged-target", entity.id), f"__TARGET_{entity.name}")
    if command_name in {"NSET", "ELSET"}:
        unique = sorted({int(value) for value in values})
        if not unique:
            raise ValueError(f"Target '{entity.name}' does not contain exported {command_name} members")
        command(writer, command_name, [(value,) for value in unique], **{command_name: name})
    elif command_name == "SURFACE":
        start = int(context.options.get("next_surface_id", 1))
        rows = [(start + index, int(element_id), side) for index, (element_id, side) in enumerate(values)]
        if not rows:
            raise ValueError(f"Surface target '{entity.name}' has no exported members")
        command(writer, "SURFACE", rows, NAME=name)
        context.options["next_surface_id"] = start + len(rows)
    else:
        raise ValueError(f"Unsupported target command '{command_name}' for '{entity.name}'")
    cache[entity.id] = name
    return name
