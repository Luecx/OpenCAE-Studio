from __future__ import annotations

import re

import numpy as np

from ..command import command
from ..element_types import element_type
from .region_resolution import resolve_members, surface_entries


def write_part_mesh(part, writer, context, instance=None, node_offset=0, element_offset=0):
    nodes = part.mesh.nodes
    if not nodes.ids or not part.mesh.element_blocks:
        writer.comment(f"Part {part.name} has no persistent generated mesh")
        return {}, {}, node_offset, element_offset
    prefix = _safe(instance.name if instance else part.name)
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
    for point, node_id in rp_records:
        set_name = f"{prefix}_RP_{_safe(point.name)}"; command(writer, "NSET", [(node_id,)], NSET=set_name)
        aliases[f"{part.name}.{point.name}"] = set_name; aliases[f"{prefix}.{point.name}"] = set_name; aliases.setdefault(point.name, set_name)
    context.options.setdefault("instance_reference_nodes", {})[prefix] = reference_nodes
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
    write_part_regions(part, writer, context, prefix, node_map, element_map, reference_nodes)
    return node_map, element_map, next_node, next_id - 1


def write_part_regions(part, writer, context, prefix, node_map, element_map, reference_nodes=None):
    for region in part.node_sets:
        _write_set(writer, "NSET", f"{prefix}_{_safe(region.name)}", region.members, node_map, part.mesh.entity_nodes, reference_nodes)
    for region in part.element_sets:
        _write_set(writer, "ELSET", f"{prefix}_{_safe(region.name)}", region.members, element_map, part.mesh.entity_elements)
    surface_id = int(context.options.get("next_surface_id", 1))
    for surface in part.surfaces:
        name = f"{prefix}_{_safe(surface.name)}"
        entries, unresolved = surface_entries(part, surface.members, node_map, element_map)
        rows = [(surface_id + index, element_id, side) for index, (element_id, side) in enumerate(entries)]
        if rows:
            command(writer, "SURFACE", rows, NAME=name)
            surface_id += len(rows)
        if unresolved:
            writer.comment(f"{name}: unresolved geometry reference(s): {', '.join(unresolved)}")
    context.options["next_surface_id"] = surface_id


def _write_set(writer, command_name, name, members, mapping, entity_members, direct=None):
    values, unresolved = resolve_members(members, mapping, entity_members, direct)
    if values:
        command(writer, command_name, [(value,) for value in values], **{command_name: name})
    if unresolved:
        writer.comment(f"{name}: unresolved reference(s): {', '.join(unresolved)}")


def _safe(value): return re.sub(r"[^A-Za-z0-9_]", "_", str(value)).upper()


def _transform(instance):
    if instance is None: return np.eye(3), np.zeros(3)
    angles = np.radians(np.asarray(instance.rotation, dtype=float)); cx, cy, cz = np.cos(angles); sx, sy, sz = np.sin(angles)
    rx = np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx))); ry = np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))); rz = np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)))
    return rz @ ry @ rx, np.asarray(instance.translation, dtype=float)


def _apply(transform, point):
    rotation, translation = transform
    return tuple(float(value) for value in rotation @ np.asarray(point, dtype=float) + translation)
