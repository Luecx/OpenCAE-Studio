from dataclasses import dataclass

from .entities.mesh.element_control import ElementOrder, ElementTopology


@dataclass(frozen=True)
class TopologyInfo:
    key: ElementTopology
    label: str
    dimension: int
    category: str
    topology: str
    primary_nodes: int
    edges: tuple[tuple[int, int], ...]
    faces: tuple[tuple[int, ...], ...] = ()
    gmsh_first: int = 0
    gmsh_second: int = 0


CATALOG = {
    ElementTopology.LINE: TopologyInfo(ElementTopology.LINE, "Line", 1, "Line Elements", "Lines", 2, ((0, 1),), gmsh_first=1, gmsh_second=8),
    ElementTopology.SHELL_TRI: TopologyInfo(ElementTopology.SHELL_TRI, "Shell – Triangle", 2, "Shell Elements", "Triangles", 3, ((0, 1), (1, 2), (2, 0)), gmsh_first=2, gmsh_second=9),
    ElementTopology.SHELL_QUAD: TopologyInfo(ElementTopology.SHELL_QUAD, "Shell – Quadrilateral", 2, "Shell Elements", "Quadrilaterals", 4, ((0, 1), (1, 2), (2, 3), (3, 0)), gmsh_first=3, gmsh_second=16),
    ElementTopology.SOLID_TET: TopologyInfo(ElementTopology.SOLID_TET, "Solid – Tetrahedral", 3, "Solid Elements", "Tetrahedra", 4, ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)), ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)), 4, 11),
    ElementTopology.SOLID_PYRAMID: TopologyInfo(ElementTopology.SOLID_PYRAMID, "Solid – Pyramidal", 3, "Solid Elements", "Pyramids", 5, ((0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)), ((0, 3, 2, 1), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)), 7, 19),
    ElementTopology.SOLID_WEDGE: TopologyInfo(ElementTopology.SOLID_WEDGE, "Solid – Wedge", 3, "Solid Elements", "Pentahedra", 6, ((0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3), (0, 3), (1, 4), (2, 5)), ((0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)), 6, 18),
    ElementTopology.SOLID_HEX: TopologyInfo(ElementTopology.SOLID_HEX, "Solid – Hexahedral", 3, "Solid Elements", "Hexahedra", 8, ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)), ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)), 5, 17),
}


def topology_key(definition) -> ElementTopology | None:
    category, topology = definition.category, definition.topology
    if category == "Line Elements": return ElementTopology.LINE
    if category in {"Shell Elements", "2D Elements"}:
        return ElementTopology.SHELL_TRI if topology == "Triangles" else ElementTopology.SHELL_QUAD if topology == "Quadrilaterals" else None
    return {"Tetrahedra": ElementTopology.SOLID_TET, "Pyramids": ElementTopology.SOLID_PYRAMID,
            "Pentahedra": ElementTopology.SOLID_WEDGE, "Hexahedra": ElementTopology.SOLID_HEX}.get(topology)


def formulations(key: ElementTopology) -> tuple[str, ...]:
    if key == ElementTopology.LINE: return ("Truss", "Beam")
    if key == ElementTopology.SHELL_TRI: return ("Standard", "Finite Rotation MITC")
    if key == ElementTopology.SHELL_QUAD: return ("Standard", "MITC", "Finite Rotation MITC")
    if key == ElementTopology.SOLID_HEX: return ("Standard", "Reduced Integration")
    return ("Standard",)


def resulting_type(key, order, formulation="Standard"):
    second = ElementOrder(order) == ElementOrder.SECOND
    if key == ElementTopology.LINE: return "LINE3" if second else ("B33" if formulation == "Beam" else "T3")
    if key == ElementTopology.SHELL_TRI: return ("MITC6FRT" if second else "MITC3FRT") if "Rotation" in formulation else ("S6" if second else "S3")
    if key == ElementTopology.SHELL_QUAD:
        if "Rotation" in formulation: return "MITC8FRT" if second else "MITC4FRT"
        if formulation == "MITC": return "MITC8" if second else "MITC4"
        return "S8" if second else "S4"
    names = {ElementTopology.SOLID_TET:("C3D4","C3D10"), ElementTopology.SOLID_PYRAMID:("C3D5","C3D13"), ElementTopology.SOLID_WEDGE:("C3D6","C3D15")}
    if key in names: return names[key][second]
    return ("C3D20R" if second else "C3D8R") if "Reduced" in formulation else ("C3D20" if second else "C3D8")
