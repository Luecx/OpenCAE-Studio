from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox

from opencae.model.geometry import GeometryFeature
from opencae.model.mesh import MeshControl, Seed
from opencae.model.regions import Region
from opencae.model.part import Part
from opencae.ui.dialogs.entity_editor import EntityEditorDialog


class SelectionController:
    def __init__(self,store,parent,part_controller=None,resource_controller=None):
        self.store=store; self.parent=parent; self.part_controller=part_controller; self.resource_controller=resource_controller
    def edit_selected(self):
        entity=self.store.selection
        if entity is None or isinstance(entity,dict):self.store.message.emit('Select an editable model object first'); return
        if self.part_controller and isinstance(entity,Part):return self.part_controller.edit_part(entity)
        if self.part_controller and isinstance(entity,Seed):return self.part_controller.edit_seed(entity)
        if self.part_controller and isinstance(entity,MeshControl):return self.part_controller.edit_mesh_control(entity)
        if self.part_controller and isinstance(entity,GeometryFeature):return self.part_controller.edit_geometry_feature(entity)
        if self.part_controller and isinstance(entity,Region):return self.part_controller.edit_region(entity)
        from opencae.model.entities.constraints import Constraint
        if isinstance(entity, Constraint):
            controller = getattr(getattr(self.parent, "controllers", None), "assembly", None)
            if controller: controller.edit_constraint(entity); return
        from opencae.model.entities.analysis.step import AnalysisStep
        if isinstance(entity, AnalysisStep):
            controller = getattr(getattr(self.parent, "controllers", None), "analysis", None)
            if controller: controller.edit_step(entity); return
        if self.resource_controller:
            from opencae.model.entities.profiles import Profile
            from opencae.model.entities.resources import Material
            from opencae.model.entities.sections import Section
            from opencae.model.entities.fields import FieldDefinition
            if isinstance(entity,(Material,Profile,Section,FieldDefinition)):
                self.resource_controller.edit(entity); return
        dialog=EntityEditorDialog(entity,self.parent)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.store.mutate(
                f"Edited {getattr(entity,'name',type(entity).__name__)}",
                lambda project:dialog.apply(),
            )
            from opencae.model.regions import CoordinateSystem
            if isinstance(entity, CoordinateSystem):
                self.store.invalidate_scene("Coordinate system edited")
    def delete_selected(self):
        entity=self.store.selection
        if entity is None:self.store.message.emit('Select a model object first'); return
        if QMessageBox.question(self.parent,'Delete object',f"Delete {getattr(entity,'name',type(entity).__name__)}?")!=QMessageBox.StandardButton.Yes:return
        if self._remove(entity):self.store.select(None)
        else:self.store.message.emit('This tree node cannot be deleted directly')
    def _remove(self, entity) -> bool:
        from opencae.model.entities.analysis.step import AnalysisStep
        if isinstance(entity, AnalysisStep):
            analysis = next((item for item in self.store.project.analyses if entity in item.steps), None)
            if analysis is not None:
                self.store.mutate(f"Deleted {entity.name}", lambda project: project.analyses.remove(analysis))
                return True
        from .entity_collections import project_collections
        for collection in project_collections(self.store.project):
            if any(item is entity for item in collection):
                self.store.mutate(
                    f"Deleted {getattr(entity, 'name', 'object')}",
                    lambda project, current=collection, selected=entity: current.remove(selected),
                )
                if self.part_controller:
                    part = self.store.active_part()
                    if part:
                        self.part_controller.service.invalidate(
                            part.id, mesh_only=not isinstance(entity, GeometryFeature),
                        )
                self.store.invalidate_scene("Deleted displayed model object")
                return True
        return False
