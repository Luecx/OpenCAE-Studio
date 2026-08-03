from __future__ import annotations


def element_side_indices(topology: str):
    """Return FEMaster side labels and corner-node indices for a topology."""
    if topology == "Tetrahedra":
        return (("S1", (0, 1, 2)), ("S2", (0, 3, 1)), ("S3", (1, 3, 2)), ("S4", (2, 3, 0)))
    if topology == "Pyramids":
        return (("S1", (0, 1, 2, 3)), ("S2", (0, 4, 1)), ("S3", (1, 4, 2)), ("S4", (2, 4, 3)), ("S5", (3, 4, 0)))
    if topology == "Pentahedra":
        return (("S1", (0, 1, 2)), ("S2", (3, 5, 4)), ("S3", (0, 3, 4, 1)), ("S4", (1, 4, 5, 2)), ("S5", (2, 5, 3, 0)))
    if topology == "Hexahedra":
        return (("S1", (0, 1, 2, 3)), ("S2", (4, 7, 6, 5)), ("S3", (0, 4, 5, 1)), ("S4", (1, 5, 6, 2)), ("S5", (2, 6, 7, 3)), ("S6", (3, 7, 4, 0)))
    return ()
