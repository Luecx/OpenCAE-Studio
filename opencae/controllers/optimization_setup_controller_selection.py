"""Owns topology Study selection, region picking, and symmetry reference picking."""

from __future__ import annotations

from opencae.controllers.region_selection import (
    begin_region_pick,
    policy_for_projection,
)
from opencae.model.entities.optimization import SymmetryType, TopologyOptimization
from opencae.model.selection import RegionProjection, SelectableKind


def current_optimization(controller):
    """Resolve the active/selected/first TopologyOptimization Study."""
    project = controller.store.project
    active = project.try_resolve(getattr(controller, "active_study_id", ""))
    if isinstance(active, TopologyOptimization):
        return active

    entity = controller.store.selection
    while entity is not None:
        if isinstance(entity, TopologyOptimization):
            controller.active_study_id = entity.id
            return project.try_resolve(entity.id)
        parent_id = project.index.parent_id.get(getattr(entity, "id", ""))
        entity = project.try_resolve(parent_id) if parent_id else None
    return project.studies[0] if project.studies else None


def require_optimization(controller) -> None:
    """Emit the standard message used when no topology Study is available."""
    controller.store.message.emit(
        "Create or select a Topology Optimization Study first"
    )


def begin_element_region_pick(controller, _selector, done, finished):
    """Begin multi-element picking for topology design/response regions."""
    policy = policy_for_projection(RegionProjection.ELEMENTS, multiple=True)
    return begin_region_pick(
        controller.store.project,
        controller.parent.viewport,
        policy,
        done,
        finished=finished,
    )


def begin_symmetry_pick(controller, symmetry_type, callback, finished) -> None:
    """Begin plane/vector picking appropriate for one symmetry type."""
    allowed = (
        {SelectableKind.GEOMETRY_FACE, SelectableKind.DATUM_PLANE}
        if symmetry_type == SymmetryType.PLANAR
        else {SelectableKind.GEOMETRY_EDGE, SelectableKind.DATUM_VECTOR}
    )

    def selected(reference) -> None:
        """Forward the pick and maintain a visible datum-reference preview."""
        callback(reference)
        controller.parent.viewport.show_datum_reference_preview((reference,))

    controller.parent.viewport.begin_datum_reference_pick(
        allowed,
        selected,
        finished=finished,
    )
