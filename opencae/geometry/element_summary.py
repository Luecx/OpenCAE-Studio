from __future__ import annotations

from opencae.model.mesh import ElementDefinition, create_element_definition


def definition_from_block(block) -> ElementDefinition:
    category, topology = neutral_type(block.name, block.dimension, block.primary_nodes)
    return create_element_definition(
        category, topology, name=topology,
        order="Quadratic" if block.order > 1 else "Linear",
        formulation="Standard", gmsh_type=block.gmsh_type,
        count=len(block.connectivity),
    )


def definitions_from_snapshot(snapshot) -> list[ElementDefinition]:
    return _merge([definition_from_block(block) for block in snapshot.blocks if block.dimension == snapshot.dimension])


def neutral_type(name: str, dimension: int, nodes: int):
    text = name.lower()
    if dimension == 1: return "Line Elements", "Lines"
    if dimension == 2:
        return "Shell Elements", "Triangles" if "triangle" in text or nodes in (3, 6) else "Quadrilaterals"
    if "tetra" in text or nodes in (4, 10): return "Solid Elements", "Tetrahedra"
    if "hexa" in text or nodes in (8, 20, 27): return "Solid Elements", "Hexahedra"
    if "prism" in text or "wedge" in text or nodes in (6, 15, 18): return "Solid Elements", "Pentahedra"
    if "pyramid" in text or nodes in (5, 13, 14): return "Solid Elements", "Pyramids"
    return "Solid Elements", name


def _merge(definitions):
    merged = {}
    for definition in definitions:
        key = (definition.category, definition.topology, definition.order, definition.gmsh_type)
        if key in merged: merged[key].count += definition.count
        else: merged[key] = definition
    return list(merged.values())
