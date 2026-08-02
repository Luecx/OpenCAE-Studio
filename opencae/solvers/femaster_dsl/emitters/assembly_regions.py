from __future__ import annotations

from ..command import command
from .mesh import _safe
from .region_resolution import resolve_members, surface_entries


def write_assembly_regions(project, exported, writer, context):
    aliases = context.options.setdefault("region_aliases", {})
    for region in project.assembly.node_sets:
        name = _safe(region.name)
        values, unresolved = _resolve(region.members, exported, "nodes", context)
        _write_ids(writer, "NSET", name, values, unresolved)
        aliases[region.name] = name
    for region in project.assembly.element_sets:
        name = _safe(region.name)
        values, unresolved = _resolve(region.members, exported, "elements", context)
        _write_ids(writer, "ELSET", name, values, unresolved)
        aliases[region.name] = name
    for region in project.assembly.surfaces:
        name = _safe(region.name)
        rows, unresolved = _surface_rows(region.members, exported, context)
        if rows: command(writer, "SURFACE", rows, NAME=name)
        if unresolved: writer.comment(f"{name}: unresolved reference(s): {', '.join(unresolved)}")
        aliases[region.name] = name


def _resolve(members, exported, kind, context):
    values, unresolved = set(), []
    direct = context.options.get("assembly_reference_nodes", {}) if kind == "nodes" else {}
    instance_direct = context.options.get("instance_reference_nodes", {}) if kind == "nodes" else {}
    for member in members:
        text = str(member)
        if text in direct: values.add(int(direct[text])); continue
        candidates, label = _candidates(text, exported)
        matched = False
        for part, instance, node_map, element_map in candidates:
            mapping = node_map if kind == "nodes" else element_map
            entity_map = part.mesh.entity_nodes if kind == "nodes" else part.mesh.entity_elements
            prefix = _safe(instance.name if instance else part.name)
            found, missing = resolve_members([label], mapping, entity_map, instance_direct.get(prefix, {}))
            if found: values.update(found); matched = True
            elif not missing: matched = True
        if not matched: unresolved.append(str(member))
    return sorted(values), unresolved


def _surface_rows(members, exported, context):
    entries, unresolved = [], []
    for member in members:
        text = str(member)
        candidates, label = _candidates(text, exported)
        matched = False
        for part, _instance, node_map, element_map in candidates:
            found, missing = surface_entries(part, [label], node_map, element_map)
            if found: entries.extend(found); matched = True
            elif not missing: matched = True
        if not matched: unresolved.append(str(member))
    start = int(context.options.get("next_surface_id", 1))
    rows = [(start + index, element_id, side) for index, (element_id, side) in enumerate(entries)]
    context.options["next_surface_id"] = start + len(rows)
    return rows, unresolved


def _candidates(member, exported):
    if "." not in member: return exported, member
    prefix, label = member.split(".", 1)
    matches = [item for item in exported if prefix in {item[0].name, getattr(item[1], "name", "")}]
    return matches, label


def _write_ids(writer, kind, name, values, unresolved):
    if values: command(writer, kind, [(value,) for value in values], **{kind: name})
    if unresolved: writer.comment(f"{name}: unresolved reference(s): {', '.join(unresolved)}")
