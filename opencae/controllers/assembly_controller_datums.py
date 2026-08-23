"""Implements Assembly coordinate-system and reference-point dialog workflows."""

from __future__ import annotations

from opencae.model.naming import next_name
from opencae.model.regions import CoordinateSystem, ReferencePoint
from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from opencae.ui.dialogs.coordinate_system import CoordinateSystemDialog
from opencae.ui.dialogs.reference_point import ReferencePointDialog


def create_coordinate_system(controller) -> None:
    """Open a modeless Assembly CoordinateSystem creation dialog."""
    assembly = controller.store.project.assembly
    dialog = CoordinateSystemDialog(
        next_name("CSYS", assembly.coordinate_systems),
        [item.name for item in assembly.coordinate_systems],
        controller.parent,
    )
    state = {"id": None}
    controller._dialogs.append(dialog)
    _connect_reference_picking(controller, dialog)

    def commit(values) -> None:
        """Insert or replace the CoordinateSystem represented by the dialog."""
        if state["id"]:
            system = CoordinateSystem(
                id=state["id"],
                name=values["name"],
                system_type=values["system_type"],
                origin=values["origin"],
                axis_1=values["axis_1"],
                axis_2=values["axis_2"],
                scope="Assembly",
            )
            controller.store.replace_entity(
                f"Updated assembly {system.name}",
                assembly.id,
                "coordinate_systems",
                system,
            )
        else:
            system = CoordinateSystem(
                name=values["name"],
                system_type=values["system_type"],
                origin=values["origin"],
                axis_1=values["axis_1"],
                axis_2=values["axis_2"],
                scope="Assembly",
            )
            controller.store.add_entity(
                f"Created assembly {system.name}",
                assembly.id,
                "coordinate_systems",
                system,
            )
            state["id"] = system.id
        controller.store.select(system)
        controller.store.invalidate_scene("Assembly coordinate system changed")

    dialog.apply_requested.connect(commit)
    dialog.finished.connect(lambda _code: controller._finish_dialog(dialog))
    show_modeless_dialog(dialog)


def create_reference_point(controller) -> None:
    """Open a modeless Assembly ReferencePoint creation dialog."""
    assembly = controller.store.project.assembly
    dialog = ReferencePointDialog(
        next_name("RP", assembly.reference_points),
        [item.name for item in assembly.reference_points],
        controller.parent,
    )
    state = {"id": None}
    controller._dialogs.append(dialog)
    _connect_reference_picking(controller, dialog)

    def commit(values) -> None:
        """Insert or replace the ReferencePoint represented by the dialog."""
        if state["id"]:
            point = ReferencePoint(
                id=state["id"],
                name=values["name"],
                position=values["position"],
                scope="Assembly",
            )
            controller.store.replace_entity(
                f"Updated assembly {point.name}",
                assembly.id,
                "reference_points",
                point,
            )
        else:
            point = ReferencePoint(
                name=values["name"],
                position=values["position"],
                scope="Assembly",
            )
            controller.store.add_entity(
                f"Created assembly {point.name}",
                assembly.id,
                "reference_points",
                point,
            )
            state["id"] = point.id
        controller.store.select(point)
        controller.store.invalidate_scene("Assembly reference point changed")

    dialog.apply_requested.connect(commit)
    dialog.finished.connect(lambda _code: controller._finish_dialog(dialog))
    show_modeless_dialog(dialog)


def _connect_reference_picking(controller, dialog) -> None:
    """Connect a datum-style dialog to the shared viewport picking lifecycle."""
    dialog.pick_requested.connect(
        lambda allowed, callback, finished: controller.parent.viewport.begin_datum_reference_pick(
            allowed,
            callback,
            finished,
        )
    )
    dialog.cancel_pick_requested.connect(
        controller.parent.viewport.cancel_context_pick
    )
