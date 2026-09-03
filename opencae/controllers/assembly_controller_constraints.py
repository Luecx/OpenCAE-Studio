"""Implements Assembly constraint creation, picking, validation, and preview."""

from __future__ import annotations

from PyQt6.QtWidgets import QInputDialog

from opencae.model.assembly import create_constraint
from opencae.model.entities.constraints import (
    ConstraintType,
    constraint_selection_policy,
    direct_control_point_error,
)
from opencae.model.naming import next_name
from opencae.model.regions import create_region
from opencae.model.selection import region_definition_error
from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from opencae.ui.dialogs.constraint import ConstraintDialog

from .region_selection import begin_region_pick, region_options


def show_constraint_dialog(
    controller,
    constraint_type="Kinematic Coupling",
    constraint=None,
) -> None:
    """Open a modeless create/edit dialog for one Assembly constraint."""
    project = controller.store.project

    def policy(kind, role):
        """Return the canonical selection policy for one constraint side."""
        normalized_role = "master" if role == "master" else "slave"
        return constraint_selection_policy(kind, normalized_role)

    def pick(kind, role, _owner, done, finished):
        """Start viewport picking using the constraint side's policy."""
        selection_policy = policy(kind, role)
        return begin_region_pick(
            controller.store.project,
            controller.parent.viewport,
            selection_policy,
            done,
            finished=finished,
        )

    def save(kind, role, _owner, definition) -> None:
        """Persist an inline picked definition as a reusable Assembly Region."""
        selection_policy = policy(kind, role)
        name, accepted = QInputDialog.getText(
            controller.parent,
            "Save Region",
            "Region name:",
            text=next_name("REGION", controller.store.project.assembly.regions),
        )
        if not accepted or not name.strip():
            return
        region = create_region(
            "Region",
            name=name.strip(),
            scope="Assembly",
            definition=definition,
            preferred_projection=selection_policy.requirement.projection,
        )
        controller.store.add_entity(
            f"Created assembly region {region.name}",
            controller.store.project.assembly.id,
            "regions",
            region,
        )

    def validate(values) -> str:
        """Return deduplicated control/slave region diagnostics for the dialog."""
        kind = ConstraintType.coerce(values["constraint_type"])
        checks = _validation_checks(kind, values, policy)
        messages = _direct_control_point_messages(kind, values)
        for definition, requirement in checks:
            error = region_definition_error(
                controller.store.project,
                definition,
                requirement,
            )
            if error:
                messages.extend(error.splitlines())
        return "\n".join(dict.fromkeys(messages))

    dialog = ConstraintDialog(
        project=project,
        options=region_options(project),
        pick_callback=pick,
        save_callback=save,
        parent=controller.parent,
        default_name=next_name(
            str(constraint_type).replace(" Coupling", ""),
            project.assembly.constraints,
        ),
        existing_names=[item.name for item in project.assembly.constraints],
        initial_type=constraint_type,
        constraint=constraint,
        validator=validate,
    )
    dialog.setModal(False)
    controller._dialogs.append(dialog)
    preview_prefix = f"constraint-dialog-{id(dialog)}"

    def preview(master, slave) -> None:
        """Show persistent visual differentiation for both constraint sides."""
        viewport = controller.parent.viewport
        viewport.suspend_model_selection_preview()
        viewport.show_region_preview(
            f"{preview_prefix}-master",
            master,
            color="#ffd166",
            opacity=.86,
            point_size=22,
            show_point_labels=True,
        )
        viewport.show_region_preview(
            f"{preview_prefix}-slave",
            slave,
            color="#42a5f5",
            opacity=.58,
            point_size=16,
            show_point_labels=False,
        )

    dialog.preview_changed.connect(preview)
    state = {"existing_id": getattr(constraint, "id", None)}

    def commit() -> None:
        """Create or replace the constraint represented by current dialog state."""
        values = dialog.values()
        kind = values.pop("constraint_type")
        existing_id = state["existing_id"]
        if existing_id:
            values["id"] = existing_id
        replacement = create_constraint(kind, **values)
        description = (
            f"{'Edited' if existing_id else 'Created'} {replacement.name}"
        )
        if existing_id:
            controller.store.replace_entity(
                description,
                controller.store.project.assembly.id,
                "constraints",
                replacement,
            )
        else:
            controller.store.add_entity(
                description,
                controller.store.project.assembly.id,
                "constraints",
                replacement,
            )
        state["existing_id"] = replacement.id
        controller.store.select(replacement)
        controller.store.invalidate_scene("Constraint changed")

    def applied() -> None:
        """Apply current values and prepare another new constraint when creating."""
        commit()
        if constraint is None:
            state["existing_id"] = None
            dialog.prepare_new(
                next_name(
                    str(constraint_type).replace(" Coupling", ""),
                    controller.store.project.assembly.constraints,
                ),
                [
                    item.name
                    for item in controller.store.project.assembly.constraints
                ],
            )

    def finish(_code) -> None:
        """Remove temporary previews and release the shared picking lifecycle."""
        controller.parent.viewport.clear_region_previews(preview_prefix)
        controller.parent.viewport.restore_model_selection_preview()
        controller._finish_dialog(dialog)

    dialog.applied.connect(applied)
    dialog.accepted.connect(commit)
    dialog.finished.connect(finish)
    show_modeless_dialog(dialog)
    preview(*dialog.preview_definitions())


def _validation_checks(kind, values, policy) -> tuple:
    """Return region-definition/requirement pairs for one constraint kind."""
    if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
        return (
            (values["control_point"], policy(kind, "master").requirement),
            (values["slave"], policy(kind, "slave").requirement),
        )
    if kind is ConstraintType.TIE:
        return (
            (values["master"], policy(kind, "master").requirement),
            (values["slave"], policy(kind, "slave").requirement),
        )
    if kind is ConstraintType.RIGID_BODY:
        return (
            (values["reference"], policy(kind, "master").requirement),
            (values["body"], policy(kind, "slave").requirement),
        )
    if kind is ConstraintType.CONNECTOR:
        return (
            (values["master"], policy(kind, "master").requirement),
            (values["slave"], policy(kind, "slave").requirement),
        )
    return ()


def _direct_control_point_messages(kind, values) -> list[str]:
    """Return direct-control-point diagnostics for constraint kinds requiring one."""
    definition = None
    if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
        definition = values["control_point"]
    elif kind is ConstraintType.RIGID_BODY:
        definition = values["reference"]
    if definition is None:
        return []
    error = direct_control_point_error(definition)
    return [error] if error else []
