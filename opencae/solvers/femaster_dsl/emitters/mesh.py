from __future__ import annotations

import re
import numpy as np

from ..command import command
from ..element_types import element_type
from .region_materialization import materialize_region


def write_part_mesh(part, writer, context, instance=None, node_offset=0, element_offset=0):
    nodes = part.mesh.nodes
    if not nodes.ids or not part.mesh.element_blocks:
        writer.comment(f"Part {part.name} has no persistent generated mesh")
        return {}, {}, node_offset, element_offset

    occurrence_id = instance.id if instance else part.id
    prefix = context.names.register(("instance", occurrence_id), instance.name if instance else part.name)
    transform = _transform(instance)
    node_map = {int(old): node_offset + index + 1 for index, old in enumerate(nodes.ids)}
    command(
        writer,
        "NODE",
        [(node_map[int(old)], *_apply(transform, point)) for old, point in zip(nodes.ids, nodes.coordinates)],
        NSET=f"{prefix}_NALL",
    )
    context.options.setdefault("instance_node_maps", {})[occurrence_id] = node_map

    next_node = max(node_map.values(), default=node_offset)
    reference_rows = []
    reference_ids = context.options.setdefault("reference_point_node_ids", {})
    legacy_reference_maps = context.options.setdefault("instance_reference_nodes", {})
    legacy_reference_map = {}
    for point in part.reference_points:
        next_node += 1
        reference_rows.append((next_node, *_apply(transform, point.position)))
        reference_ids[(occurrence_id, point.id)] = next_node
        legacy_reference_map[point.name] = next_node
        legacy_reference_map[f"RP-{point.name}"] = next_node
    if reference_rows:
        command(writer, "NODE", reference_rows, NSET=f"{prefix}_REFERENCE_POINTS")
    legacy_reference_maps[occurrence_id] = legacy_reference_map
    legacy_reference_maps[prefix] = legacy_reference_map

    aliases = context.options.setdefault("region_aliases", {})
    entity_aliases = context.options.setdefault("entity_aliases", {})
    part_aliases = context.options.setdefault("part_region_aliases", {})
    for point in part.reference_points:
        node_id = reference_ids[(occurrence_id, point.id)]
        set_name = context.names.register(("reference-point", occurrence_id, point.id), f"{prefix}_RP_{_safe(point.name)}")
        command(writer, "NSET", [(node_id,)], NSET=set_name)
        aliases[f"{prefix}.{point.name}"] = set_name
        part_aliases.setdefault(point.id, []).append(set_name)
        entity_aliases[(occurrence_id, point.id)] = set_name

    element_map = {}
    next_element = element_offset + 1
    for index, block in enumerate(part.mesh.element_blocks, 1):
        type_name = element_type(block.definition, len(block.connectivity[0]) if block.connectivity else None)
        if type_name is None:
            writer.comment(f"No FEMaster element mapping for {block.definition.category}/{block.definition.topology}")
            continue
        rows = []
        for old_id, connectivity in zip(block.ids, block.connectivity):
            element_map[int(old_id)] = next_element
            rows.append((next_element, *(node_map[int(node)] for node in connectivity)))
            next_element += 1
        command(writer, "ELEMENT", rows, TYPE=type_name, ELSET=f"{prefix}_E{index}")
    if next_element > element_offset + 1:
        command(writer, "ELSET", [(value,) for value in range(element_offset + 1, next_element)], ELSET=f"{prefix}_EALL")
    context.options.setdefault("instance_element_maps", {})[occurrence_id] = element_map

    write_part_regions(part, writer, context, prefix, instance)
    return node_map, element_map, next_node, next_element - 1


def write_part_regions(part, writer, context, prefix, instance=None):
    occurrence_id = instance.id if instance else part.id
    instance_aliases = context.options.setdefault("instance_region_aliases", {})
    part_aliases = context.options.setdefault("part_region_aliases", {})
    entity_aliases = context.options.setdefault("entity_aliases", {})
    aliases = context.options.setdefault("region_aliases", {})

    for region in part.regions:
        projection = region.preferred_projection
        if projection is None:
            writer.comment(f"Region {prefix}.{region.name} has no preferred solver projection and was not exported")
            continue
        materialized = materialize_region(
            region.definition,
            projection,
            writer,
            context,
            owner=region,
            proposed_name=f"{prefix}_{_safe(region.name)}",
            instance_id=occurrence_id,
            cache_key=("named-part-region", occurrence_id, region.id),
        )
        instance_aliases[(occurrence_id, region.id)] = materialized.name
        part_aliases.setdefault(region.id, []).append(materialized.name)
        entity_aliases[(occurrence_id, region.id)] = materialized.name
        aliases[f"{prefix}.{region.name}"] = materialized.name


def _safe(value):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(value)).upper()


def _transform(instance):
    if instance is None:
        return np.eye(3), np.zeros(3)
    angles = np.radians(np.asarray(instance.rotation, dtype=float))
    cx, cy, cz = np.cos(angles)
    sx, sy, sz = np.sin(angles)
    rx = np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx)))
    ry = np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)))
    rz = np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)))
    return rz @ ry @ rx, np.asarray(instance.translation, dtype=float)


def _apply(transform, point):
    rotation, translation = transform
    return tuple(float(value) for value in rotation @ np.asarray(point, dtype=float) + translation)
