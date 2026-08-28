from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import QDialog, QInputDialog, QMessageBox

from opencae.model.geometry import GeometryFeature
from opencae.model.mesh import ElementControl, Seed
from opencae.model.part import Part
from opencae.model.regions import Region
from opencae.model.selection import ViewportSelection
from opencae.store.commands import CompositeCommand, entity_collection_location, make_delete_command, make_replace_command
from opencae.ui.dialogs.entity_editor import EntityEditorDialog


class SelectionController:
    def __init__(self, store, parent, part_controller=None, resource_controller=None):
        self.store = store
        self.parent = parent
        self.part_controller = part_controller
        self.resource_controller = resource_controller

    def edit_selected(self):
        entity = self.store.selection
        if entity is None or isinstance(entity, ViewportSelection):
            self.store.message.emit("Select an editable model object first")
            return
        if self.part_controller and isinstance(entity, Part):
            return self.part_controller.edit_part(entity)
        if self.part_controller and isinstance(entity, Seed):
            return self.part_controller.edit_seed(entity)
        if self.part_controller and isinstance(entity, ElementControl):
            return self.part_controller.edit_element_control(entity)
        if self.part_controller and isinstance(entity, GeometryFeature):
            return self.part_controller.edit_geometry_feature(entity)

        # Datum planes currently contain structured geometric references.
        # Sending them through the generic dataclass editor exposes those
        # references as meaningless string fields.  Until a dedicated datum
        # editing workflow exists, datum planes are intentionally immutable.
        from opencae.model.entities.datums import DatumPlane
        if isinstance(entity, DatumPlane):
            self.store.message.emit(
                "Datum planes cannot be edited yet. Delete and recreate the plane instead."
            )
            return

        from opencae.model.entities.regions import SectionAssignment
        if self.part_controller and isinstance(entity, SectionAssignment):
            return self.part_controller.edit_assignment(entity)
        if isinstance(entity, Region):
            assembly = self.store.project.assembly
            if self.store.project.index.parent_id.get(entity.id) == assembly.id:
                return self.parent.controllers.assembly.edit_region(entity)
            if self.part_controller:
                return self.part_controller.edit_region(entity)

        from opencae.model.entities.assembly import Instance
        if isinstance(entity, Instance):
            return self.parent.controllers.assembly.edit_instance(entity)

        from opencae.model.entities.constraints import Constraint
        if isinstance(entity, Constraint):
            return self.parent.controllers.assembly.edit_constraint(entity)

        from opencae.model.entities.amplitudes import Amplitude
        from opencae.model.entities.loads import Load
        from opencae.model.entities.supports import Support
        if isinstance(entity, (Amplitude, Load, Support)):
            return self.parent.controllers.loads.edit(entity)

        from opencae.model.entities.analysis.step import AnalysisStep
        if isinstance(entity, AnalysisStep):
            return self.parent.controllers.analysis.edit_step(entity)

        if self.resource_controller:
            from opencae.model.entities.fields import FieldDefinition
            from opencae.model.entities.profiles import Profile
            from opencae.model.entities.resources import Material
            from opencae.model.entities.sections import Section
            if isinstance(entity, (Material, Profile, Section, FieldDefinition)):
                return self.resource_controller.edit(entity)

        candidate = deepcopy(entity)
        dialog = EntityEditorDialog(candidate, self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        dialog.apply()
        try:
            parent_id, attribute = entity_collection_location(self.store.project, entity.id)
        except ValueError as exc:
            self.store.message.emit(str(exc))
            return
        self.store.replace_entity(f"Edited {getattr(entity, 'name', type(entity).__name__)}", parent_id, attribute, candidate)
        from opencae.model.regions import CoordinateSystem
        if isinstance(entity, CoordinateSystem):
            self.store.invalidate_scene("Coordinate system edited")

    def delete_selected(self):
        entity = self.store.selection
        if entity is None or isinstance(entity, ViewportSelection):
            self.store.message.emit("Select a model object first")
            return
        project = self.store.project
        uses = [use for use in project.references_to(entity.id) if use.source_id != entity.id]
        if not uses:
            if QMessageBox.question(self.parent, "Delete object", f"Delete {entity.name}?") != QMessageBox.StandardButton.Yes:
                return
            self._delete_direct(entity)
            return
        self._delete_referenced(entity, uses)

    def _delete_referenced(self, entity, uses):
        from opencae.model.core import compatible_replacements

        lines = [f"• {use.source_name} — {use.field_path}" for use in uses[:12]]
        if len(uses) > 12:
            lines.append(f"• … and {len(uses) - 12} more")
        box = QMessageBox(self.parent)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Object is referenced")
        box.setText(f'Cannot delete "{entity.name}" without resolving its references.')
        box.setInformativeText("Referenced by:\n" + "\n".join(lines))
        replace_button = box.addButton("Replace References", QMessageBox.ButtonRole.ActionRole)
        cascade_button = box.addButton("Delete Dependents", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is replace_button:
            candidates = compatible_replacements(self.store.project, entity)
            if not candidates:
                QMessageBox.information(self.parent, "No replacement", "No type-compatible replacement exists in the current project.")
                return
            labels = [self._replacement_label(item) for item in candidates]
            label, accepted = QInputDialog.getItem(self.parent, "Replace references", f"Replace {entity.name} with", labels, 0, False)
            if not accepted:
                return
            replacement = candidates[labels.index(label)]
            command = self._replace_and_delete_command(entity.id, replacement)
            self.store.execute(f"Replaced references to {entity.name}", command)
            self._after_delete(entity)
        elif clicked is cascade_button:
            command = self._cascade_delete_command(entity.id)
            self.store.execute(f"Deleted {entity.name} and dependents", command)
            self._after_delete(entity)

    def _delete_direct(self, entity):
        try:
            parent_id, attribute = entity_collection_location(self.store.project, entity.id)
        except ValueError:
            self.store.message.emit("This tree node cannot be deleted directly")
            return
        self.store.delete_entity(f"Deleted {entity.name}", parent_id, attribute, entity.id)
        self._after_delete(entity)

    def _replace_and_delete_command(self, old_id, replacement):
        from opencae.model.core import entity_with_replaced_references

        project = self.store.project
        commands = []
        source_ids = sorted({use.source_id for use in project.references_to(old_id) if use.source_id != old_id})
        for source_id in source_ids:
            source = project.try_resolve(source_id)
            if source is None:
                continue
            candidate, changed = entity_with_replaced_references(source, old_id, replacement)
            if not changed:
                continue
            parent_id, attribute = entity_collection_location(project, source_id)
            commands.append(make_replace_command(project, parent_id, attribute, candidate))
        parent_id, attribute = entity_collection_location(project, old_id)
        commands.append(make_delete_command(project, parent_id, attribute, old_id))
        return CompositeCommand(tuple(commands))

    def _cascade_delete_command(self, root_id):
        from opencae.model.core import cascade_entity_ids

        project = self.store.project
        ids = cascade_entity_ids(project, root_id)
        roots = [entity_id for entity_id in ids if project.index.parent_id.get(entity_id) not in ids]
        commands = []
        for entity_id in sorted(roots, key=lambda value: project.index.path.get(value, ""), reverse=True):
            parent_id, attribute = entity_collection_location(project, entity_id)
            commands.append(make_delete_command(project, parent_id, attribute, entity_id))
        if not commands:
            raise ValueError("The selected entity graph cannot be deleted")
        return CompositeCommand(tuple(commands))

    def _replacement_label(self, entity):
        path = self.store.project.index.path.get(entity.id, "")
        return f"{entity.name} — {path}"

    def _after_delete(self, entity):
        self.store.select(None)
        if self.part_controller:
            part = self.store.active_part()
            if part:
                self.part_controller.service.invalidate(part.id, mesh_only=not isinstance(entity, GeometryFeature))
        self.store.invalidate_scene("Deleted displayed model object")
