from opencae.model.selection import (
    RegionProjection, RegionRequirement, SelectableKind, SelectionPolicy,
)


SUPPORT_REGION_REQUIREMENT = RegionRequirement(RegionProjection.NODES, (0, 1, 2, 3), 1)


def support_selection_policy() -> SelectionPolicy:
    return SelectionPolicy.create({
        SelectableKind.GEOMETRY_VERTEX, SelectableKind.GEOMETRY_EDGE,
        SelectableKind.GEOMETRY_FACE, SelectableKind.GEOMETRY_CELL,
        SelectableKind.MESH_NODE, SelectableKind.MESH_ELEMENT,
        SelectableKind.REFERENCE_POINT,
    }, multiple=True, requirement=SUPPORT_REGION_REQUIREMENT)
