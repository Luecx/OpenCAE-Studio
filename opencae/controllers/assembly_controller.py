from __future__ import annotations

from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from PyQt6.QtWidgets import QInputDialog

from opencae.model.assembly import Instance, create_constraint
from opencae.model.core import EntityRef
from opencae.model.entities.constraints import ConstraintType, constraint_selection_policy, direct_control_point_error
from opencae.model.naming import next_name
from opencae.model.regions import CoordinateSystem, ReferencePoint, create_region
from opencae.model.selection import (
    region_definition_error,
)
from opencae.store.commands import UpdateFieldCommand
from opencae.ui.dialogs.constraint import ConstraintDialog
from opencae.ui.dialogs.coordinate_system import CoordinateSystemDialog
from opencae.ui.dialogs.instance import InstanceDialog
from opencae.ui.dialogs.reference_point import ReferencePointDialog
from opencae.ui.dialogs.transform_instance import TransformInstanceDialog
from .assembly_regions import AssemblyRegions
from .dialog_runner import get_values
from .region_selection import begin_region_pick, region_options


class AssemblyController:
    def __init__(self, store, parent, part_controller=None):
        self.store = store
        self.parent = parent
        self.part_controller = part_controller
        self.regions = AssemblyRegions(self)
        self._dialogs = []

    def _create_part(self, parent, done):
        before = {part.id for part in self.store.project.parts}
        self.part_controller.new_part(parent=parent)
        done(next((part for part in self.store.project.parts if part.id not in before), None))

    def add_instance(self): self._instance_dialog()
    def edit_instance(self, instance): self._instance_dialog(instance)

    def _instance_dialog(self, instance=None):
        project = self.store.project
        dialog = InstanceDialog(
            project.parts, self._create_part,
            [item.name for item in project.assembly.instances], self.parent,
            next_name("Instance", project.assembly.instances), instance,
        )
        dialog.setModal(False)
        self._dialogs.append(dialog)
        state = {"existing_id": getattr(instance, "id", None)}

        def commit():
            existing_id = state["existing_id"]
            current = self.store.project.try_resolve(existing_id) if existing_id else None
            values = dialog.values()
            value = Instance(
                id=existing_id or None,
                name=values["name"],
                part_ref=EntityRef(values["part_id"], "Part"),
                translation=current.translation if current else (0.0, 0.0, 0.0),
                rotation=current.rotation if current else (0.0, 0.0, 0.0),
                suppressed=current.suppressed if current else False,
            ) if existing_id else Instance(
                name=values["name"],
                part_ref=EntityRef(values["part_id"], "Part"),
            )
            description = f"{'Edited' if existing_id else 'Added'} instance {value.name}"
            if existing_id:
                self.store.replace_entity(description, self.store.project.assembly.id, "instances", value)
            else:
                self.store.add_entity(description, self.store.project.assembly.id, "instances", value)
            state["existing_id"] = value.id
            self.store.select(value)
            self.store.invalidate_scene("Assembly instance changed")

        dialog.applied.connect(commit)
        dialog.accepted.connect(commit)
        dialog.finished.connect(lambda _code: self._finish_dialog(dialog))
        show_modeless_dialog(dialog)

    def _finish_dialog(self, dialog):
        if hasattr(self.parent, "viewport"):
            self.parent.viewport.cancel_context_pick()
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)

    def duplicate_instance(self):
        if not self.store.project.assembly.instances:
            return
        source = self.store.project.assembly.instances[-1]
        part = self.store.project.try_resolve(source.part_ref)
        value = Instance(
            name=next_name(part.name if part else "Instance", self.store.project.assembly.instances),
            part_ref=source.part_ref,
            translation=source.translation,
            rotation=source.rotation,
            suppressed=source.suppressed,
        )
        self.store.add_entity(f"Duplicated {source.name}", self.store.project.assembly.id, "instances", value)
        self.store.invalidate_scene("Assembly instance duplicated")

    def transform(self):
        values = get_values(TransformInstanceDialog(self.store.project.assembly.instances, self.parent))
        instance = self.store.project.try_resolve(values["instance_id"]) if values else None
        if not instance:
            return
        attribute = "translation" if values["operation"] == "Translate" else "rotation"
        vector = (values["x"], values["y"], values["z"])
        command = UpdateFieldCommand(instance.id, attribute, getattr(instance, attribute), vector)
        self.store.execute(f"{values['operation']} {instance.name}", command)
        self.store.invalidate_scene("Assembly instance transformed")

    def suppress_instance(self):
        if not self.store.project.assembly.instances:
            return
        instance = self.store.project.assembly.instances[-1]
        command = UpdateFieldCommand(instance.id, "suppressed", instance.suppressed, not instance.suppressed)
        self.store.execute(f"Suppressed {instance.name}", command)
        self.store.invalidate_scene("Assembly instance visibility changed")

    def node_set(self): self.regions.node_set()
    def element_set(self): self.regions.element_set()
    def surface(self): self.regions.surface()
    def edit_region(self, region): return self.regions.edit(region)

    def coordinate_system(self):
        values = get_values(CoordinateSystemDialog(
            next_name("CSYS", self.store.project.assembly.coordinate_systems),
            [item.name for item in self.store.project.assembly.coordinate_systems],
            self.parent,
        ))
        if not values:
            return
        system = CoordinateSystem(
            name=values["name"], system_type=values["system_type"],
            origin=values["origin"], axis_1=values["axis_1"], axis_2=values["axis_2"],
            scope="Assembly",
        )
        self.store.add_entity(f"Created assembly {system.name}", self.store.project.assembly.id, "coordinate_systems", system)
        self.store.invalidate_scene("Assembly coordinate system created")

    def reference_point(self):
        values = get_values(ReferencePointDialog(
            next_name("RP", self.store.project.assembly.reference_points),
            [item.name for item in self.store.project.assembly.reference_points],
            self.parent,
        ))
        if not values:
            return
        point = ReferencePoint(
            name=values["name"], position=(values["x"], values["y"], values["z"]),
            scope="Assembly",
        )
        self.store.add_entity(f"Created assembly {point.name}", self.store.project.assembly.id, "reference_points", point)

    def constraint(self, constraint_type="Kinematic Coupling"):
        self._constraint_dialog(constraint_type)

    def edit_constraint(self, constraint):
        self._constraint_dialog(constraint.constraint_type, constraint)

    def _constraint_policy(self, kind, role):
        return constraint_selection_policy(kind, role)

    def _constraint_dialog(self, constraint_type, constraint=None):
        project = self.store.project

        def pick(kind, role, _owner, done, finished):
            policy = self._constraint_policy(kind, "master" if role == "master" else "slave")
            return begin_region_pick(
                self.store.project, self.parent.viewport, policy, done, finished=finished
            )

        def save(kind, role, _owner, definition):
            policy = self._constraint_policy(kind, "master" if role == "master" else "slave")
            name, ok = QInputDialog.getText(
                self.parent, "Save Region", "Region name:",
                text=next_name("REGION", self.store.project.assembly.regions),
            )
            if not ok or not name.strip():
                return
            region = create_region(
                "Region", name=name.strip(), scope="Assembly", definition=definition,
                preferred_projection=policy.requirement.projection,
            )
            self.store.add_entity(
                f"Created assembly region {region.name}",
                self.store.project.assembly.id, "regions", region,
            )

        def validate(values):
            kind = ConstraintType.coerce(values["constraint_type"])
            if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
                checks = (
                    (values["control_point"], self._constraint_policy(kind, "master").requirement),
                    (values["slave"], self._constraint_policy(kind, "slave").requirement),
                )
            elif kind == ConstraintType.TIE:
                checks = (
                    (values["master"], self._constraint_policy(kind, "master").requirement),
                    (values["slave"], self._constraint_policy(kind, "slave").requirement),
                )
            elif kind == ConstraintType.RIGID_BODY:
                checks = (
                    (values["reference"], self._constraint_policy(kind, "master").requirement),
                    (values["body"], self._constraint_policy(kind, "slave").requirement),
                )
            else:
                checks = ()
            messages = []
            if kind in {ConstraintType.KINEMATIC, ConstraintType.DISTRIBUTING}:
                error = direct_control_point_error(values["control_point"])
                if error:
                    messages.append(error)
            elif kind == ConstraintType.RIGID_BODY:
                error = direct_control_point_error(values["reference"])
                if error:
                    messages.append(error)
            for definition, requirement in checks:
                error = region_definition_error(self.store.project, definition, requirement)
                if error:
                    messages.extend(error.splitlines())
            return "\n".join(dict.fromkeys(messages))

        dialog = ConstraintDialog(
            project=project, options=region_options(project), pick_callback=pick,
            save_callback=save, parent=self.parent,
            default_name=next_name(str(constraint_type).replace(" Coupling", ""), project.assembly.constraints),
            existing_names=[item.name for item in project.assembly.constraints],
            initial_type=constraint_type, constraint=constraint, validator=validate,
        )
        dialog.setModal(False)
        self._dialogs.append(dialog)
        preview_prefix = f"constraint-dialog-{id(dialog)}"

        def preview(master, slave):
            viewport = self.parent.viewport
            viewport.show_region_preview(
                f"{preview_prefix}-master", master, color="#ffd166",
                opacity=.86, point_size=22, show_point_labels=True,
            )
            viewport.show_region_preview(
                f"{preview_prefix}-slave", slave, color="#42a5f5",
                opacity=.58, point_size=16, show_point_labels=False,
            )

        dialog.preview_changed.connect(preview)
        state = {"existing_id": getattr(constraint, "id", None)}

        def commit():
            values = dialog.values()
            kind = values.pop("constraint_type")
            existing_id = state["existing_id"]
            if existing_id:
                values["id"] = existing_id
            replacement = create_constraint(kind, **values)
            description = f"{'Edited' if existing_id else 'Created'} {replacement.name}"
            if existing_id:
                self.store.replace_entity(description, self.store.project.assembly.id, "constraints", replacement)
            else:
                self.store.add_entity(description, self.store.project.assembly.id, "constraints", replacement)
            state["existing_id"] = replacement.id
            self.store.select(replacement)
            self.store.invalidate_scene("Constraint changed")

        def applied():
            commit()
            if constraint is None:
                state["existing_id"] = None
                dialog.prepare_new(
                    next_name(str(constraint_type).replace(" Coupling", ""), self.store.project.assembly.constraints),
                    [item.name for item in self.store.project.assembly.constraints],
                )

        def finish(_code):
            self.parent.viewport.clear_region_previews(preview_prefix)
            self._finish_dialog(dialog)

        dialog.applied.connect(applied)
        dialog.accepted.connect(commit)
        dialog.finished.connect(finish)
        show_modeless_dialog(dialog)
        preview(*dialog.preview_definitions())
