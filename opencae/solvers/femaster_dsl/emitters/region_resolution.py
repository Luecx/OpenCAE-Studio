from __future__ import annotations

import re

_LABEL = re.compile(r"^(?:Node|Element)-(\d+)$", re.IGNORECASE)


def resolve_members(members, explicit_map, entity_members, direct=None):
    values = set()
    unresolved = []
    direct = direct or {}
    for member in members:
        text = str(member)
        if text in direct:
            values.add(int(direct[text])); continue
        match = _LABEL.match(text)
        if match and int(match.group(1)) in explicit_map:
            values.add(explicit_map[int(match.group(1))])
            continue
        if text.isdigit() and int(text) in explicit_map:
            values.add(explicit_map[int(text)])
            continue
        associated = entity_members.get(text)
        if associated is None:
            unresolved.append(text)
            continue
        values.update(explicit_map[value] for value in associated if value in explicit_map)
    return sorted(values), unresolved


def surface_entries(part, members, node_map, element_map):
    boundary_nodes = set()
    shell_elements = set()
    unresolved = []
    for member in members:
        nodes = part.mesh.entity_nodes.get(str(member))
        elements = part.mesh.entity_elements.get(str(member))
        if nodes is None and elements is None:
            unresolved.append(str(member))
            continue
        boundary_nodes.update(nodes or ())
        shell_elements.update(elements or ())
    entries = []
    for block in part.mesh.element_blocks:
        category = block.definition.category
        for old_id, connectivity in zip(block.ids, block.connectivity):
            if old_id not in element_map:
                continue
            if category in {"Shell Elements", "2D Elements"}:
                if old_id in shell_elements:
                    entries.append((element_map[old_id], "SPOS"))
                continue
            for side, indices in side_indices(block.definition.topology):
                corner_nodes = {connectivity[index] for index in indices if index < len(connectivity)}
                if corner_nodes and corner_nodes.issubset(boundary_nodes):
                    entries.append((element_map[old_id], side))
                    break
    return entries, unresolved


def side_indices(topology):
    if topology == "Tetrahedra":
        return (("S1", (0, 1, 2)), ("S2", (0, 3, 1)), ("S3", (1, 3, 2)), ("S4", (2, 3, 0)))
    if topology == "Pyramids":
        return (("S1", (0, 1, 2, 3)), ("S2", (0, 4, 1)), ("S3", (1, 4, 2)), ("S4", (2, 4, 3)), ("S5", (3, 4, 0)))
    if topology == "Pentahedra":
        return (("S1", (0, 1, 2)), ("S2", (3, 5, 4)), ("S3", (0, 3, 4, 1)), ("S4", (1, 4, 5, 2)), ("S5", (2, 5, 3, 0)))
    if topology == "Hexahedra":
        return (("S1", (0, 1, 2, 3)), ("S2", (4, 7, 6, 5)), ("S3", (0, 4, 5, 1)), ("S4", (1, 5, 6, 2)), ("S5", (2, 6, 7, 3)), ("S6", (3, 7, 4, 0)))
    return ()
