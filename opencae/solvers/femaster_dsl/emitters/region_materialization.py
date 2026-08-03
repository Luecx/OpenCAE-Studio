from __future__ import annotations

from dataclasses import dataclass
import re

from opencae.model.selection import RegionDefinition, RegionProjection, RegionRequirement, RegionResolver
from ..command import command


@dataclass(frozen=True, slots=True)
class MaterializedRegion:
    name: str
    projection: RegionProjection
    count: int


def materialize_region(
    definition: RegionDefinition,
    projection: RegionProjection | str,
    writer,
    context,
    *,
    owner,
    proposed_name: str,
    instance_id: str = "",
    cache_key=None,
    allowed_dimensions=(0, 1, 2, 3),
    min_count: int = 1,
    max_count: int | None = None,
    require_unique_occurrence: bool = False,
) -> MaterializedRegion:
    projection = RegionProjection(projection)
    key = cache_key if cache_key is not None else ("inline-region", getattr(owner, "id", id(owner)), projection, instance_id)
    cache = context.options.setdefault("materialized_regions", {})
    cache_key_full = (key, projection.value, instance_id)
    if cache_key_full in cache:
        return cache[cache_key_full]

    requirement = RegionRequirement(
        projection=projection,
        allowed_dimensions=allowed_dimensions,
        min_count=min_count,
        max_count=max_count,
        require_unique_occurrence=require_unique_occurrence,
    )
    resolved = RegionResolver(context.project).resolve(definition, requirement, instance_id=instance_id)
    errors = [item.message for item in resolved.diagnostics if item.severity == "error"]
    if errors:
        label = getattr(owner, "name", type(owner).__name__)
        raise ValueError(f"Region of '{label}' cannot be resolved: " + "; ".join(errors))

    command_name = "NSET" if projection in {RegionProjection.NODES, RegionProjection.SINGLE_CONTROL_NODE} else "ELSET" if projection == RegionProjection.ELEMENTS else "SURFACE"
    name = context.names.register(("region", key, projection.value, instance_id), proposed_name)
    if command_name == "NSET":
        values = _node_ids(resolved, context)
        command(writer, "NSET", [(value,) for value in values], NSET=name)
    elif command_name == "ELSET":
        values = _element_ids(resolved, context)
        command(writer, "ELSET", [(value,) for value in values], ELSET=name)
    else:
        values = _facet_rows(resolved, context)
        start = int(context.options.get("next_surface_id", 1))
        rows = [(start + index, element_id, side) for index, (element_id, side) in enumerate(values)]
        command(writer, "SURFACE", rows, NAME=name)
        context.options["next_surface_id"] = start + len(rows)

    result = MaterializedRegion(name, projection, len(values))
    cache[cache_key_full] = result
    return result


def _node_ids(resolved, context):
    values = set()
    maps = context.options.get("instance_node_maps", {})
    for occurrence in resolved.nodes:
        mapping = maps.get(occurrence.instance_id or occurrence.owner_id, {})
        if int(occurrence.node_id) not in mapping:
            raise ValueError(f"Node {occurrence.node_id} has no exported occurrence '{occurrence.instance_id or occurrence.owner_id}'")
        values.add(int(mapping[int(occurrence.node_id)]))
    reference_nodes = context.options.get("reference_point_node_ids", {})
    for occurrence in resolved.reference_points:
        node_id = reference_nodes.get((occurrence.instance_id, occurrence.reference_point_id))
        if node_id is None:
            node_id = reference_nodes.get(("", occurrence.reference_point_id))
        if node_id is None:
            raise ValueError(f"Reference point '{occurrence.reference_point_id}' has no exported node")
        values.add(int(node_id))
    return sorted(values)


def _element_ids(resolved, context):
    values = set()
    maps = context.options.get("instance_element_maps", {})
    for occurrence in resolved.elements:
        mapping = maps.get(occurrence.instance_id or occurrence.owner_id, {})
        if int(occurrence.element_id) not in mapping:
            raise ValueError(f"Element {occurrence.element_id} has no exported occurrence '{occurrence.instance_id or occurrence.owner_id}'")
        values.add(int(mapping[int(occurrence.element_id)]))
    return sorted(values)


def _facet_rows(resolved, context):
    values = set()
    maps = context.options.get("instance_element_maps", {})
    for occurrence in resolved.facets:
        mapping = maps.get(occurrence.instance_id or occurrence.owner_id, {})
        if int(occurrence.element_id) not in mapping:
            raise ValueError(f"Facet element {occurrence.element_id} has no exported occurrence '{occurrence.instance_id or occurrence.owner_id}'")
        values.add((int(mapping[int(occurrence.element_id)]), str(occurrence.local_face)))
    return sorted(values)


def safe_name(value) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", str(value)).upper()
