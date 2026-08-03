from __future__ import annotations

from opencae.model.selection import (
    GeometryOperand,
    MeshNodeOperand,
    ReferencePointOperand,
    RegionDefinition,
    RegionProjection,
    RegionRequirement,
    SelectableKind,
    SelectionPolicy,
)

from .types import ConstraintType


_POINT_KINDS = {
    SelectableKind.GEOMETRY_VERTEX,
    SelectableKind.MESH_NODE,
    SelectableKind.REFERENCE_POINT,
}
_NODE_REGION_KINDS = {
    SelectableKind.GEOMETRY_VERTEX,
    SelectableKind.GEOMETRY_EDGE,
    SelectableKind.GEOMETRY_FACE,
    SelectableKind.GEOMETRY_CELL,
    SelectableKind.MESH_NODE,
    SelectableKind.MESH_ELEMENT,
    SelectableKind.REFERENCE_POINT,
}
_FACET_KINDS = {
    SelectableKind.GEOMETRY_FACE,
    SelectableKind.MESH_ELEMENT,
    SelectableKind.MESH_FACET,
}
_ELEMENT_KINDS = {
    SelectableKind.GEOMETRY_EDGE,
    SelectableKind.GEOMETRY_FACE,
    SelectableKind.GEOMETRY_CELL,
    SelectableKind.MESH_ELEMENT,
}


def constraint_region_requirement(kind, role: str) -> RegionRequirement:
    """Return the one authoritative semantic requirement for a constraint field."""
    kind = ConstraintType.coerce(kind)
    role = str(role).casefold()
    master = role in {"master", "control", "control_point", "reference"}
    if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
        return (
            RegionRequirement(RegionProjection.SINGLE_CONTROL_NODE, (0,), 1, 1, True)
            if master
            else RegionRequirement(RegionProjection.NODES, (0, 1, 2, 3), 1)
        )
    if kind == ConstraintType.TIE:
        return RegionRequirement(RegionProjection.FACETS, (2,), 1)
    if kind == ConstraintType.RIGID_BODY:
        return (
            RegionRequirement(RegionProjection.SINGLE_CONTROL_NODE, (0,), 1, 1, True)
            if master
            else RegionRequirement(RegionProjection.ELEMENTS, (1, 2, 3), 1)
        )
    return RegionRequirement(RegionProjection.NODES, (0, 1, 2, 3), 1)


def constraint_selection_policy(kind, role: str) -> SelectionPolicy:
    kind = ConstraintType.coerce(kind)
    requirement = constraint_region_requirement(kind, role)
    master = str(role).casefold() in {"master", "control", "control_point", "reference"}
    if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING} and master:
        kinds = _POINT_KINDS
    elif kind == ConstraintType.TIE:
        kinds = _FACET_KINDS
    elif kind == ConstraintType.RIGID_BODY and master:
        kinds = _POINT_KINDS
    elif kind == ConstraintType.RIGID_BODY:
        kinds = _ELEMENT_KINDS
    else:
        kinds = _NODE_REGION_KINDS
    return SelectionPolicy.create(kinds, multiple=not master or kind == ConstraintType.TIE, requirement=requirement)


def direct_control_point_error(definition) -> str:
    """Require one directly selected vertex, mesh node, or reference point.

    Named regions are intentionally rejected here even when they would resolve
    to one node.  Coupling control points are explicit visual point picks.
    """
    items = RegionDefinition.from_values(definition).items
    if len(items) != 1:
        return "Select exactly one control point in the viewport."
    operand = items[0].operand
    if isinstance(operand, GeometryOperand) and operand.dimension == 0:
        return ""
    if isinstance(operand, (MeshNodeOperand, ReferencePointOperand)):
        return ""
    return "The control point must be a directly selected vertex, mesh node, or reference point; named regions are not allowed."
