"""Implements Instance creation, duplication, transforms, and suppression."""

from __future__ import annotations

from opencae.model.assembly import Instance
from opencae.model.core import EntityRef
from opencae.model.naming import next_name
from opencae.store.commands import UpdateFieldCommand
from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from opencae.ui.dialogs.instance import InstanceDialog
from opencae.ui.dialogs.transform_instance import TransformInstanceDialog

from .dialog_runner import get_values


def show_instance_dialog(controller, instance=None) -> None:
    """Open the reusable modeless create/edit Instance dialog."""
    project = controller.store.project
    dialog = InstanceDialog(
        project.parts,
        controller._create_part,
        [item.name for item in project.assembly.instances],
        controller.parent,
        next_name("Instance", project.assembly.instances),
        instance,
    )
    dialog.setModal(False)
    controller._dialogs.append(dialog)
    state = {"existing_id": getattr(instance, "id", None)}

    def commit() -> None:
        """Persist the current dialog values while preserving transform state."""
        existing_id = state["existing_id"]
        current = (
            controller.store.project.try_resolve(existing_id)
            if existing_id
            else None
        )
        values = dialog.values()
        if existing_id:
            value = Instance(
                id=existing_id,
                name=values["name"],
                part_ref=EntityRef(values["part_id"], "Part"),
                translation=current.translation,
                rotation=current.rotation,
                suppressed=current.suppressed,
            )
        else:
            value = Instance(
                name=values["name"],
                part_ref=EntityRef(values["part_id"], "Part"),
            )

        description = (
            f"{'Edited' if existing_id else 'Added'} instance {value.name}"
        )
        if existing_id:
            controller.store.replace_entity(
                description,
                controller.store.project.assembly.id,
                "instances",
                value,
            )
        else:
            controller.store.add_entity(
                description,
                controller.store.project.assembly.id,
                "instances",
                value,
            )
        state["existing_id"] = value.id
        controller.store.select(value)
        controller.store.invalidate_scene("Assembly instance changed")

    dialog.applied.connect(commit)
    dialog.accepted.connect(commit)
    dialog.finished.connect(lambda _code: controller._finish_dialog(dialog))
    show_modeless_dialog(dialog)


def duplicate_instance(controller) -> None:
    """Duplicate the last assembly Instance while preserving its transform."""
    instances = controller.store.project.assembly.instances
    if not instances:
        return
    source = instances[-1]
    part = controller.store.project.try_resolve(source.part_ref)
    value = Instance(
        name=next_name(part.name if part else "Instance", instances),
        part_ref=source.part_ref,
        translation=source.translation,
        rotation=source.rotation,
        suppressed=source.suppressed,
    )
    controller.store.add_entity(
        f"Duplicated {source.name}",
        controller.store.project.assembly.id,
        "instances",
        value,
    )
    controller.store.invalidate_scene("Assembly instance duplicated")


def transform_instance(controller) -> None:
    """Apply one translation or rotation to the user-selected Instance."""
    values = get_values(
        TransformInstanceDialog(
            controller.store.project.assembly.instances,
            controller.parent,
        )
    )
    instance = (
        controller.store.project.try_resolve(values["instance_id"])
        if values
        else None
    )
    if not instance:
        return

    attribute = (
        "translation" if values["operation"] == "Translate" else "rotation"
    )
    vector = (values["x"], values["y"], values["z"])
    command = UpdateFieldCommand(
        instance.id,
        attribute,
        getattr(instance, attribute),
        vector,
    )
    controller.store.execute(
        f"{values['operation']} {instance.name}",
        command,
    )
    controller.store.invalidate_scene("Assembly instance transformed")


def toggle_instance_suppression(controller) -> None:
    """Toggle suppression for the last assembly Instance through undoable state."""
    instances = controller.store.project.assembly.instances
    if not instances:
        return
    instance = instances[-1]
    command = UpdateFieldCommand(
        instance.id,
        "suppressed",
        instance.suppressed,
        not instance.suppressed,
    )
    controller.store.execute(f"Suppressed {instance.name}", command)
    controller.store.invalidate_scene("Assembly instance visibility changed")
