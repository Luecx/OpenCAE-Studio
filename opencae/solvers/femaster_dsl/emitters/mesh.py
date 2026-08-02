from __future__ import annotations

import re

import numpy as np

from ..command import command
from ..element_types import element_type
from .region_resolution import resolve_members, surface_entries
from opencae.model.core import region_member_local_label


def write_part_mesh(part, writer, context, instance=None, node_offset=0, element_offset=0):
    nodes = part.mesh.nodes
    if not nodes.ids or not part.mesh.element_blocks:
        writer.comment(f"Part {part.name} has no persistent generated mesh")
        return {}, {}, node_offset, element_offset
    prefix = context.names.register(("instance", instance.id if instance else part.id), instance.name if instance else part.name)
    transform = _transform(instance)
    node_map = {int(old): node_offset + i + 1 for i, old in enumerate(nodes.ids)}
    command(writer, "NODE", [(node_map[int(old)], *_apply(transform, point)) for old, point in zip(nodes.ids, nodes.coordinates)], NSET=f"{prefix}_NALL")
    next_node = max(node_map.values(), default=node_offset)
    reference_nodes = {}; rp_rows = []; rp_records = []
    for point in part.reference_points:
        next_node += 1; reference_nodes[f"RP-{point.name}"] = next_node; reference_nodes[point.name] = next_node
        rp_rows.append((next_node, *_apply(transform, point.position))); rp_records.append((point, next_node))
    if rp_rows: command(writer, "NODE", rp_rows, NSET=f"{prefix}_REFERENCE_POINTS")
    aliases = context.options.setdefault("region_aliases", {})
    part_aliases = context.options.setdefault("part_region_aliases", {})
    part_data = context.options.setdefault("part_region_data", {})
    for point, node_id in rp_records:
        set_name = context.names.register(((instance.id if instance else part.id), point.id), f"{prefix}_RP_{_safe(point.name)}")
        command(writer, "NSET", [(node_id,)], NSET=set_name)
        aliases[f"{part.name}.{point.name}"] = set_name; aliases[f"{prefix}.{point.name}"] = set_name; aliases.setdefault(point.name, set_name)
        part_aliases.setdefault(point.id, []).append(set_name)
        record = part_data.setdefault(point.id, {"command": "NSET", "values": []}); record["values"].append(node_id)
    reference_maps = context.options.setdefault("instance_reference_nodes", {})
    reference_maps[prefix] = reference_nodes
    reference_maps[instance.id if instance else part.id] = reference_nodes
    element_map = {}; next_id = element_offset + 1
    for index, block in enumerate(part.mesh.element_blocks, 1):
        type_name = element_type(block.definition, len(block.connectivity[0]) if block.connectivity else None)
        if type_name is None:
            writer.comment(f"No FEMaster element mapping for {block.definition.category}/{block.definition.topology}")
            continue
        rows = []
        for old_id, connectivity in zip(block.ids, block.connectivity):
            element_map[int(old_id)] = next_id
            rows.append((next_id, *(node_map[int(node)] for node in connectivity)))
            next_id += 1
        command(writer, "ELEMENT", rows, TYPE=type_name, ELSET=f"{prefix}_E{index}")
    if next_id > element_offset + 1:
        command(writer, "ELSET", [(value,) for value in range(element_offset + 1, next_id)], ELSET=f"{prefix}_EALL")
    context.options.setdefault("instance_node_maps", {})[instance.id if instance else part.id] = node_map
    context.options.setdefault("instance_element_maps", {})[instance.id if instance else part.id] = element_map
    write_part_regions(part, writer, context, prefix, node_map, element_map, reference_nodes, instance)
    return node_map, element_map, next_node, next_id - 1


def write_part_regions(part, writer, context, prefix, node_map, element_map, reference_nodes=None, instance=None):
    instance_aliases = context.options.setdefault("instance_region_aliases", {}); part_aliases = context.options.setdefault("part_region_aliases", {}); part_data = context.options.setdefault("part_region_data", {})
    owner_id = instance.id if instance else part.id
    for region in part.node_sets:
        name = context.names.register((owner_id, region.id), f"{prefix}_{_safe(region.name)}"); members = [region_member_local_label(context.project, item) for item in region.members]; values = _write_set(writer, "NSET", name, members, node_map, part.mesh.entity_nodes, reference_nodes)
        instance_aliases[(owner_id, region.id)] = name; part_aliases.setdefault(region.id, []).append(name); part_data.setdefault(region.id, {"command": "NSET", "values": []})["values"].extend(values)
    for region in part.element_sets:
        name = context.names.register((owner_id, region.id), f"{prefix}_{_safe(region.name)}"); members = [region_member_local_label(context.project, item) for item in region.members]; values = _write_set(writer, "ELSET", name, members, element_map, part.mesh.entity_elements)
        instance_aliases[(owner_id, region.id)] = name; part_aliases.setdefault(region.id, []).append(name); part_data.setdefault(region.id, {"command": "ELSET", "values": []})["values"].extend(values)
    surface_id = int(context.options.get("next_surface_id", 1))
    for surface in part.surfaces:
        name = context.names.register((owner_id, surface.id), f"{prefix}_{_safe(surface.name)}"); instance_aliases[(owner_id, surface.id)] = name; part_aliases.setdefault(surface.id, []).append(name)
        members = [region_member_local_label(context.project, item) for item in surface.members]
        entries, unresolved = surface_entries(part, members, node_map, element_map)
        rows = [(surface_id + index, element_id, side) for index, (element_id, side) in enumerate(entries)]
        if rows:
            command(writer, "SURFACE", rows, NAME=name)
            surface_id += len(rows)
            part_data.setdefault(surface.id, {"command": "SURFACE", "values": []})["values"].extend(entries)
        if unresolved:
            writer.comment(f"{name}: unresolved geometry reference(s): {', '.join(unresolved)}")
    context.options["next_surface_id"] = surface_id


def _write_set(writer, command_name, name, members, mapping, entity_members, direct=None):
    values, unresolved = resolve_members(members, mapping, entity_members, direct)
    if values:
        command(writer, command_name, [(value,) for value in values], **{command_name: name})
    if unresolved:
        writer.comment(f"{name}: unresolved reference(s): {', '.join(unresolved)}")
    return values


def _safe(value): return re.sub(r"[^A-Za-z0-9_]", "_", str(value)).upper()


def _transform(instance):
    if instance is None: return np.eye(3), np.zeros(3)
    angles = np.radians(np.asarray(instance.rotation, dtype=float)); cx, cy, cz = np.cos(angles); sx, sy, sz = np.sin(angles)
    rx = np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx))); ry = np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))); rz = np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)))
    return rz @ ry @ rx, np.asarray(instance.translation, dtype=float)


def _apply(transform, point):
    rotation, translation = transform
    return tuple(float(value) for value in rotation @ np.asarray(point, dtype=float) + translation)
