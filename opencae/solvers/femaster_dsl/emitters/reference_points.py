from ..command import command
from .mesh import _safe


def write_assembly_reference_points(project, writer, context, node_offset):
    rows = []; mapping = {}; aliases = context.options.setdefault("region_aliases", {}); next_node = node_offset
    records = []
    for point in project.assembly.reference_points:
        next_node += 1; rows.append((next_node, *point.position)); records.append((point, next_node))
        mapping[f"RP-{point.name}"] = next_node; mapping[point.name] = next_node
    if rows: command(writer, "NODE", rows, NSET="ASSEMBLY_REFERENCE_POINTS")
    for point, node_id in records:
        set_name = f"ASSEMBLY_RP_{_safe(point.name)}"; command(writer, "NSET", [(node_id,)], NSET=set_name)
        aliases[point.name] = set_name; aliases[f"RP-{point.name}"] = set_name
    context.options["assembly_reference_nodes"] = mapping
    return next_node
