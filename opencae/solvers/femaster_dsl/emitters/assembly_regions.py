from __future__ import annotations

from opencae.model.core import RegionMemberRef, region_member_label, region_member_local_label

from ..command import command
from .mesh import _safe
from .region_resolution import resolve_members, surface_entries


def write_assembly_regions(project, exported, writer, context):
    aliases = context.options.setdefault("region_aliases", {}); entity_aliases = context.options.setdefault("entity_aliases", {})
    for region in project.assembly.node_sets:
        name = context.names.register(region.id, region.name); values, unresolved = _resolve(project, region.members, exported, "nodes", context); _write_ids(writer, "NSET", name, values, unresolved); aliases[region.name] = name; entity_aliases[region.id] = name
    for region in project.assembly.element_sets:
        name = context.names.register(region.id, region.name); values, unresolved = _resolve(project, region.members, exported, "elements", context); _write_ids(writer, "ELSET", name, values, unresolved); aliases[region.name] = name; entity_aliases[region.id] = name
    for region in project.assembly.surfaces:
        name = context.names.register(region.id, region.name); rows, unresolved = _surface_rows(project, region.members, exported, context)
        if rows: command(writer, "SURFACE", rows, NAME=name)
        if unresolved: writer.comment(f"{name}: unresolved reference(s): {', '.join(unresolved)}")
        aliases[region.name] = name; entity_aliases[region.id] = name


def _resolve(project, members, exported, kind, context):
    values, unresolved = set(), []
    direct = context.options.get("assembly_reference_nodes", {}) if kind == "nodes" else {}
    instance_direct = context.options.get("instance_reference_nodes", {}) if kind == "nodes" else {}
    for member in members:
        label = region_member_local_label(project, member)
        if label in direct:
            values.add(int(direct[label])); continue
        candidates = _candidates(project, member, exported)
        matched = False
        for part, instance, node_map, element_map in candidates:
            mapping = node_map if kind == "nodes" else element_map
            entity_map = part.mesh.entity_nodes if kind == "nodes" else part.mesh.entity_elements
            owner_id = instance.id if instance else part.id
            prefix = _safe(instance.name if instance else part.name)
            found, missing = resolve_members([label], mapping, entity_map, instance_direct.get(owner_id, instance_direct.get(prefix, {})))
            if found:
                values.update(found); matched = True
            elif not missing:
                matched = True
        if not matched:
            unresolved.append(region_member_label(project, member))
    return sorted(values), unresolved


def _surface_rows(project, members, exported, context):
    entries, unresolved = [], []
    for member in members:
        label = region_member_local_label(project, member)
        candidates = _candidates(project, member, exported)
        matched = False
        for part, _instance, node_map, element_map in candidates:
            found, missing = surface_entries(part, [label], node_map, element_map)
            if found:
                entries.extend(found); matched = True
            elif not missing:
                matched = True
        if not matched:
            unresolved.append(region_member_label(project, member))
    start = int(context.options.get("next_surface_id", 1)); rows = [(start + index, element_id, side) for index, (element_id, side) in enumerate(entries)]; context.options["next_surface_id"] = start + len(rows)
    return rows, unresolved


def _candidates(project, member, exported):
    if isinstance(member, RegionMemberRef) and member.owner_ref.entity_id:
        owner_id = member.owner_ref.entity_id
        return [
            item for item in exported
            if owner_id in {item[0].id, getattr(item[1], "id", None)}
        ]
    text = region_member_label(project, member)
    if "." not in text:
        return exported
    prefix, _label = text.split(".", 1)
    return [item for item in exported if prefix in {item[0].name, getattr(item[1], "name", "")}]


def _write_ids(writer, kind, name, values, unresolved):
    if values: command(writer, kind, [(value,) for value in values], **{kind: name})
    if unresolved: writer.comment(f"{name}: unresolved reference(s): {', '.join(unresolved)}")
