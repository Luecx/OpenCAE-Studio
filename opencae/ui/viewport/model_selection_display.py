from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import QTimer

from opencae.model.selection import (
    MeshElementOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    RegionDefinition,
    RegionSelectionItem,
    ViewportSelection,
)
from opencae.ui.core.theme import PALETTE

_MODEL_SELECTION_PREFIX = "model-selection"


def show_model_selection(viewport, entity):
    """Display the regions owned by the object selected in the project tree."""
    from opencae.model.entities.constraints import Constraint
    from opencae.model.entities.fields import FieldDefinition
    from opencae.model.regions import Region

    if not isinstance(entity, ViewportSelection):
        viewport.clear_region_previews(_MODEL_SELECTION_PREFIX)
        _refresh_coupling_overlay(viewport)

    visibility = getattr(viewport, "visibility", None)
    if (
        not isinstance(entity, ViewportSelection)
        and entity is not None
        and visibility is not None
        and not visibility.is_entity_visible(entity)
    ):
        viewport._pending_members = None
        viewport.picker.clear(False, False)
        viewport.scene.region_overlay.clear(viewport.plotter)
        viewport.plotter.render()
        return

    if isinstance(entity, FieldDefinition):
        viewport._field_id = entity.id
        if viewport.display_mode != "mesh":
            viewport.set_display_mode("mesh")
        elif viewport.scene.mesh_grid is not None:
            viewport.scene.show_field(entity)
        return

    if isinstance(entity, Constraint):
        master, slave = _constraint_definitions(entity)
        expanded_master = _expanded(viewport.store.project, master)
        expanded_slave = _expanded(viewport.store.project, slave)
        target = (
            "mesh"
            if _contains_mesh_operands(expanded_master)
            or _contains_mesh_operands(expanded_slave)
            else "geometry"
        )

        viewport.picker.clear(False, False)
        viewport.scene.region_overlay.clear(viewport.plotter)
        if viewport.display_mode != target:
            viewport.set_display_mode(target)

        viewport.show_region_preview(
            f"{_MODEL_SELECTION_PREFIX}-master",
            master,
            color=PALETTE["datum"],
            opacity=.90,
            point_size=23,
            show_point_labels=True,
        )
        viewport.show_region_preview(
            f"{_MODEL_SELECTION_PREFIX}-slave",
            slave,
            color=PALETTE["selection_3d"],
            opacity=.62,
            point_size=17,
            show_point_labels=False,
        )
        _refresh_coupling_overlay(viewport)
        return

    if isinstance(entity, Region):
        definition = _expanded(viewport.store.project, entity.definition)
        viewport._pending_members = definition
        target = "mesh" if _contains_mesh_operands(definition) else "geometry"
        if viewport.display_mode != target:
            viewport.set_display_mode(target)
        else:
            QTimer.singleShot(0, viewport._show_pending_members)
        return

    if viewport._field_id is not None and not isinstance(entity, ViewportSelection):
        viewport._field_id = None
        viewport.request_refresh()
    elif not isinstance(entity, ViewportSelection):
        viewport.picker.clear(False)
        viewport.scene.region_overlay.clear(viewport.plotter)
        viewport.plotter.render()


def show_pending_members(viewport):
    if viewport._pending_members is None:
        return
    definition = RegionDefinition.from_values(viewport._pending_members)
    viewport._pending_members = None
    viewport.picker.show_labels(definition, render=False)
    viewport.scene.region_overlay.show(viewport.plotter, viewport.scene, definition)
    viewport.plotter.render()


def highlight_members(viewport, members):
    viewport._pending_members = RegionDefinition.from_values(members)
    QTimer.singleShot(0, viewport._show_pending_members)


def _constraint_definitions(constraint):
    master = getattr(
        constraint,
        "control_point",
        getattr(constraint, "reference", getattr(constraint, "master", RegionDefinition())),
    )
    slave = getattr(
        constraint,
        "body",
        getattr(constraint, "slave", RegionDefinition()),
    )
    return RegionDefinition.from_values(master), RegionDefinition.from_values(slave)


def _refresh_coupling_overlay(viewport):
    if viewport.stage not in {"CONSTRAINTS", "BOUNDARY CONDITIONS"}:
        return
    viewport.scene.coupling_overlay.show(
        viewport.plotter, viewport.store.project, viewport.scene
    )
    viewport.plotter.render()


def _contains_mesh_operands(definition):
    return any(
        isinstance(item.operand, (MeshNodeOperand, MeshElementOperand, MeshFacetOperand))
        for item in definition.items
    )


def _expanded(project, definition, inherited_instance=None, stack=None):
    stack = set(stack or ())
    result = []
    for item in RegionDefinition.from_values(definition).items:
        operand = item.operand
        if isinstance(operand, NamedRegionOperand):
            region = project.try_resolve(operand.region_ref)
            if region is None or region.id in stack:
                continue
            instance_ref = operand.instance_ref or inherited_instance
            result.extend(
                _expanded(
                    project,
                    region.definition,
                    instance_ref,
                    {*stack, region.id},
                ).items
            )
            continue
        if (
            inherited_instance
            and hasattr(operand, "instance_ref")
            and operand.instance_ref is None
        ):
            operand = replace(operand, instance_ref=inherited_instance)
            item = RegionSelectionItem(
                operand, item.picked_position, item.display_label
            )
        result.append(item)
    return RegionDefinition(tuple(result))
