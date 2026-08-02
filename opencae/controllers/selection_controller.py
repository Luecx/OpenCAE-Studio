from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QInputDialog, QMessageBox

from opencae.model.geometry import GeometryFeature
from opencae.model.mesh import ElementControl, MeshControl, Seed
from opencae.model.part import Part
from opencae.model.regions import Region
from opencae.ui.dialogs.entity_editor import EntityEditorDialog


class SelectionController:
    def __init__(self, store, parent, part_controller=None, resource_controller=None):
        self.store = store
        self.parent = parent
        self.part_controller = part_controller
        self.resource_controller = resource_controller

    def edit_selected(self):
        entity = self.store.selection
        if entity is None or isinstance(entity, dict):
            self.store.message.emit("Select an editable model object first")
            return
        if self.part_controller and isinstance(entity, Part):
            return self.part_controller.edit_part(entity)
        if self.part_controller and isinstance(entity, Seed):
            return self.part_controller.edit_seed(entity)
        if self.part_controller and isinstance(entity, MeshControl):
            return self.part_controller.edit_mesh_control(entity)
        if self.part_controller and isinstance(entity, ElementControl):
            return self.part_controller.edit_element_control(entity)
        if self.part_controller and isinstance(entity, GeometryFeature):
            return self.part_controller.edit_geometry_feature(entity)

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

        from opencae.model.entities.loads import Load
        from opencae.model.entities.supports import Support
        if isinstance(entity, (Load, Support)):
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

        dialog = EntityEditorDialog(entity, self.parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.mutate(f"Edited {getattr(entity, 'name', type(entity).__name__)}", lambda project: dialog.apply())
            from opencae.model.regions import CoordinateSystem
            if isinstance(entity, CoordinateSystem):
                self.store.invalidate_scene("Coordinate system edited")

    def delete_selected(self):
        entity = self.store.selection
        if entity is None or isinstance(entity, dict):
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
        from opencae.model.core import compatible_replacements, delete_entity_graph, remove_entity, replace_references

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
            labels = [candidate.name for candidate in candidates]
            label, accepted = QInputDialog.getItem(self.parent, "Replace references", f"Replace {entity.name} with", labels, 0, False)
            if not accepted:
                return
            replacement = candidates[labels.index(label)]

            def apply(project):
                replace_references(project, entity.id, replacement)
                remove_entity(project, entity.id)

            self.store.mutate(f"Replaced references to {entity.name}", apply)
            self._after_delete(entity)
        elif clicked is cascade_button:
            self.store.mutate(f"Deleted {entity.name} and dependents", lambda project: delete_entity_graph(project, entity.id))
            self._after_delete(entity)

    def _delete_direct(self, entity):
        from opencae.model.core import remove_entity
        removed = {"value": False}

        def apply(project):
            removed["value"] = remove_entity(project, entity.id)

        self.store.mutate(f"Deleted {entity.name}", apply)
        if removed["value"]:
            self._after_delete(entity)
        else:
            self.store.message.emit("This tree node cannot be deleted directly")

    def _after_delete(self, entity):
        self.store.select(None)
        if self.part_controller:
            part = self.store.active_part()
            if part:
                self.part_controller.service.invalidate(part.id, mesh_only=not isinstance(entity, GeometryFeature))
        self.store.invalidate_scene("Deleted displayed model object")
