from ..command import command
from .mesh import _safe


def write_assembly_reference_points(project, writer, context, node_offset):
    rows = []
    next_node = node_offset
    reference_ids = context.options.setdefault("reference_point_node_ids", {})
    legacy_mapping = {}
    aliases = context.options.setdefault("region_aliases", {})
    entity_aliases = context.options.setdefault("entity_aliases", {})

    for point in project.assembly.reference_points:
        next_node += 1
        rows.append((next_node, *point.position))
        reference_ids[("", point.id)] = next_node
        reference_ids[(project.assembly.id, point.id)] = next_node
        legacy_mapping[point.name] = next_node
        legacy_mapping[f"RP-{point.name}"] = next_node
    if rows:
        command(writer, "NODE", rows, NSET="ASSEMBLY_REFERENCE_POINTS")

    for point in project.assembly.reference_points:
        node_id = reference_ids[("", point.id)]
        set_name = context.names.register(("assembly-rp", point.id), f"ASSEMBLY_RP_{_safe(point.name)}")
        command(writer, "NSET", [(node_id,)], NSET=set_name)
        aliases[point.name] = set_name
        aliases[f"RP-{point.name}"] = set_name
        entity_aliases[("", point.id)] = set_name
        entity_aliases[point.id] = set_name

    context.options["assembly_reference_nodes"] = legacy_mapping
    return next_node
