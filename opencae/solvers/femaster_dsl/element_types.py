ELEMENT_TYPES = {
    "C3D4", "C3D5", "C3D6", "C3D8", "C3D8R", "C3D10", "C3D13", "C3D15", "C3D20", "C3D20R",
    "S3", "MITC3FRT", "S4", "MITC4", "MITC4FRT", "S6", "MITC6FRT", "S8", "MITC8", "MITC8FRT", "QSPT",
    "B33", "T3",
}


def element_type(definition, node_count=None):
    category, topology = definition.category, definition.topology
    quadratic = definition.order == "Quadratic" or (node_count or 0) > {"Tetrahedra": 4, "Pyramids": 5, "Pentahedra": 6, "Hexahedra": 8, "Triangles": 3, "Quadrilaterals": 4}.get(topology, 2)
    reduced = "reduced" in definition.formulation.lower()
    if category == "Solid Elements":
        mapping = {("Tetrahedra", False): "C3D4", ("Tetrahedra", True): "C3D10", ("Pyramids", False): "C3D5", ("Pyramids", True): "C3D13", ("Pentahedra", False): "C3D6", ("Pentahedra", True): "C3D15", ("Hexahedra", False): "C3D8R" if reduced else "C3D8", ("Hexahedra", True): "C3D20R" if reduced else "C3D20"}
        return mapping.get((topology, quadratic))
    if category in {"Shell Elements", "2D Elements"}:
        if topology == "Triangles": return "S6" if quadratic else "S3"
        if topology == "Quadrilaterals": return "S8" if quadratic else ("MITC4" if "mitc" in definition.formulation.lower() else "S4")
    if topology == "Beam Elements": return "B33"
    if topology in {"Truss Elements", "Lines"}: return "T3"
    return None
