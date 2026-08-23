"""Formats current typed selection operands for user-facing labels."""

from __future__ import annotations

from .operands import (
    GeometryOperand,
    MeshElementOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    ReferencePointOperand,
    UnresolvedOperand,
    WholeModelOperand,
)


def selection_item_label(project, item) -> str:
    """Return a display label for one typed Region selection item."""
    if item.display_label:
        return item.display_label
    value = item.operand
    prefix = _instance_name(project, getattr(value, "instance_ref", None))
    if isinstance(value, GeometryOperand):
        label = f"{('Vertex', 'Edge', 'Face', 'Cell')[value.dimension]}-{value.tag}"
    elif isinstance(value, MeshNodeOperand):
        label = f"Node-{value.node_id}"
    elif isinstance(value, MeshElementOperand):
        label = f"Element-{value.element_id}"
    elif isinstance(value, MeshFacetOperand):
        label = f"Element-{value.element_id}.{value.local_face}"
    elif isinstance(value, ReferencePointOperand):
        label = _name(project, value.reference_point_ref, "Reference Point")
    elif isinstance(value, NamedRegionOperand):
        label = _name(project, value.region_ref, "Region")
    elif isinstance(value, WholeModelOperand):
        label = "Whole model"
    elif isinstance(value, UnresolvedOperand):
        label = value.legacy_label or "Unresolved selection"
    else:
        label = type(value).__name__
    return f"{prefix}.{label}" if prefix else label


def selection_item_kind(item) -> str:
    """Return a title-cased selection kind label."""
    return item.operand.kind.value.replace("_", " ").title()


def _instance_name(project, ref):
    entity = project.try_resolve(ref) if project is not None and ref else None
    return entity.name if entity else ""


def _name(project, ref, fallback):
    entity = project.try_resolve(ref) if project is not None else None
    return entity.name if entity else fallback
