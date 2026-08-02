from copy import deepcopy

from PyQt6.QtWidgets import QDialog

from opencae.model.assembly import Instance, create_constraint
from opencae.model.core import EntityRef, members_from_selection, region_member_label
from opencae.model.entities.constraints import ConstraintReference, ConstraintReferenceKind
from opencae.model.naming import next_name
from opencae.model.regions import CoordinateSystem, ReferencePoint, create_region
from opencae.ui.dialogs.constraint import ConstraintDialog
from opencae.ui.dialogs.coordinate_system import CoordinateSystemDialog
from opencae.ui.dialogs.instance import InstanceDialog
from opencae.ui.dialogs.reference_point import ReferencePointDialog
from opencae.ui.dialogs.surface import SurfaceDialog
from opencae.ui.dialogs.transform_instance import TransformInstanceDialog
from .dialog_runner import get_values
from .assembly_regions import AssemblyRegions
from .reference_pick import begin_reference_pick


class AssemblyController:
    def __init__(self,store,parent,part_controller=None):
        self.store=store; self.parent=parent; self.part_controller=part_controller; self.regions=AssemblyRegions(self); self._dialogs=[]

    def _create_part(self,parent=None):
        before={part.id for part in self.store.project.parts}; self.part_controller.new_part(parent=parent); return next((part for part in self.store.project.parts if part.id not in before),None)

    def add_instance(self): self._instance_dialog()
    def edit_instance(self, instance): self._instance_dialog(instance)

    def _instance_dialog(self, instance=None):
        project=self.store.project
        dialog=InstanceDialog(project.parts,self._create_part,[i.name for i in project.assembly.instances],self.parent,next_name("Instance",project.assembly.instances),instance)
        dialog.setModal(False); self._dialogs.append(dialog); state={"existing":instance}

        def commit():
            current=state["existing"]; values=dialog.values(); kwargs=dict(
                name=values["name"], part_ref=EntityRef(values["part_id"],"Part"),
                translation=current.translation if current else (0,0,0),
                rotation=current.rotation if current else (0,0,0),
                suppressed=current.suppressed if current else False,
            )
            value=Instance(id=current.id,**kwargs) if current else Instance(**kwargs)
            def apply(current_project):
                collection=current_project.assembly.instances
                if current is None: collection.append(value)
                else:
                    index=next(i for i,item in enumerate(collection) if item.id==current.id); collection[index]=value
            self.store.mutate(f"{'Edited' if current else 'Added'} instance {value.name}",apply)
            state["existing"]=value; self.store.select(value); self.store.invalidate_scene("Assembly instance changed")

        dialog.applied.connect(commit); dialog.accepted.connect(commit)
        dialog.finished.connect(lambda _code:self._dialogs.remove(dialog) if dialog in self._dialogs else None)
        dialog.show(); dialog.raise_(); dialog.activateWindow()


    def _finish_dialog(self, dialog):
        if hasattr(self.parent, "viewport"):
            self.parent.viewport.cancel_context_pick()
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)

    def duplicate_instance(self):
        if not self.store.project.assembly.instances:return
        src=self.store.project.assembly.instances[-1]; part=self.store.project.try_resolve(src.part_ref); name=next_name(part.name if part else "Instance",self.store.project.assembly.instances)
        self.store.mutate(f"Duplicated {src.name}",lambda p:p.assembly.instances.append(Instance(name=name,part_ref=src.part_ref,translation=src.translation,rotation=src.rotation))); self.store.invalidate_scene("Assembly instance duplicated")

    def transform(self):
        values=get_values(TransformInstanceDialog(self.store.project.assembly.instances,self.parent)); instance=self.store.project.try_resolve(values["instance_id"]) if values else None
        if not instance:return
        attr="translation" if values["operation"]=="Translate" else "rotation"; vector=(values["x"],values["y"],values["z"]); self.store.mutate(f"{values['operation']} {instance.name}",lambda p:setattr(instance,attr,vector)); self.store.invalidate_scene("Assembly instance transformed")

    def suppress_instance(self):
        if self.store.project.assembly.instances:
            value=self.store.project.assembly.instances[-1]; self.store.mutate(f"Suppressed {value.name}",lambda p:setattr(value,"suppressed",not value.suppressed)); self.store.invalidate_scene("Assembly instance visibility changed")

    def _selection_labels(self):
        return members_from_selection(self.store.project, self.store.selection)

    def node_set(self):self.regions.node_set()
    def element_set(self):self.regions.element_set()
    def surface(self):self.regions.surface()
    def edit_region(self, region): return self.regions.edit(region)

    def coordinate_system(self):
        values=get_values(CoordinateSystemDialog(next_name("CSYS",self.store.project.assembly.coordinate_systems),[i.name for i in self.store.project.assembly.coordinate_systems],self.parent))
        if values:self.store.mutate(f"Created assembly {values['name']}",lambda p:p.assembly.coordinate_systems.append(CoordinateSystem(name=values["name"],system_type=values["system_type"],origin=values["origin"],axis_1=values["axis_1"],axis_2=values["axis_2"],scope="Assembly"))); self.store.invalidate_scene("Assembly coordinate system created")

    def reference_point(self):
        values=get_values(ReferencePointDialog(next_name("RP",self.store.project.assembly.reference_points),[i.name for i in self.store.project.assembly.reference_points],self.parent))
        if values:self.store.mutate(f"Created assembly {values['name']}",lambda p:p.assembly.reference_points.append(ReferencePoint(name=values["name"],position=(values["x"],values["y"],values["z"]),scope="Assembly")))

    def constraint(self,constraint_type="Kinematic Coupling"):self._constraint_dialog(constraint_type)
    def edit_constraint(self,constraint):self._constraint_dialog(constraint.constraint_type,constraint)

    def _constraint_dialog(self,constraint_type,constraint=None):
        project=self.store.project
        masters=list(project.assembly.reference_points)
        slaves=[*project.assembly.node_sets, *project.assembly.element_sets, *project.assembly.surfaces]
        def create_master(owner=None):
            values=get_values(ReferencePointDialog(next_name("RP",project.assembly.reference_points),[i.name for i in project.assembly.reference_points],owner or self.parent))
            if not values:return None
            point=ReferencePoint(name=values["name"],position=(values["x"],values["y"],values["z"]),scope="Assembly"); self.store.mutate(f"Created assembly {point.name}",lambda p:p.assembly.reference_points.append(point)); return point
        pick_master=lambda _owner,done:begin_reference_pick(self.parent.viewport,project.assembly.reference_points,{"rp"},done)
        slave_entities=[*project.assembly.node_sets,*project.assembly.element_sets,*project.assembly.surfaces]
        pick_slave=lambda _owner,done:begin_reference_pick(self.parent.viewport,slave_entities,{"point","face","cell","element"},done)
        dialog=ConstraintDialog(masters,slaves,create_master,lambda owner,done:self._nested_surface(owner,done),self.parent,next_name(str(constraint_type).replace(" Coupling",""),project.assembly.constraints),[i.name for i in project.assembly.constraints],constraint_type,constraint,pick_master,pick_slave); dialog.setModal(False); self._dialogs.append(dialog)
        state={"existing":constraint}
        def accepted():
            current=state["existing"]; values=dialog.values(); kind=values.pop("constraint_type")
            if current: values["id"]=current.id
            values={key:value for key,value in values.items() if value is not None}; replacement=create_constraint(kind,**values)
            def apply(current_project):
                collection=current_project.assembly.constraints
                if current is None: collection.append(replacement)
                else:
                    index=next(i for i,item in enumerate(collection) if item.id==current.id); collection[index]=replacement
            self.store.mutate(f"{'Edited' if current else 'Created'} {replacement.name}",apply)
            state["existing"]=replacement; self.store.select(replacement); self.store.invalidate_scene("Constraint changed")
        def applied():
            accepted()
            if constraint is None:
                state["existing"]=None
                dialog.prepare_new(next_name(str(constraint_type).replace(" Coupling",""),project.assembly.constraints),[i.name for i in project.assembly.constraints])
        dialog.applied.connect(applied); dialog.accepted.connect(accepted); dialog.finished.connect(lambda _code:self._finish_dialog(dialog)); dialog.show(); dialog.raise_(); dialog.activateWindow()

    def _nested_surface(self,owner,done):
        owner.hide(); dialog=SurfaceDialog(selection_provider=self._selection_labels,default_name=next_name("SURFACE",self.store.project.assembly.surfaces),existing_names=[i.name for i in self.store.project.assembly.surfaces],parent=self.parent,member_formatter=lambda member:region_member_label(self.store.project,member)); previous=self.parent.viewport.selection_mode; self.parent.viewport.set_selection_mode(dialog.mode()); slot=lambda _value:dialog.update_selection(); self.store.selection_changed.connect(slot)
        def restore():
            try:self.store.selection_changed.disconnect(slot)
            except Exception:pass
            self.parent.viewport.set_selection_mode(previous); owner.show(); owner.raise_(); owner.activateWindow()
        def commit(values):
            region=create_region("Surface",scope="Assembly",**values); self.store.mutate(f"Created assembly {region.name}",lambda p:p.assembly.surfaces.append(region)); done(region); dialog.close()
        dialog.selection_mode.currentTextChanged.connect(lambda _text:self.parent.viewport.set_selection_mode(dialog.mode())); dialog.committed.connect(commit); dialog.finished.connect(lambda _code:restore()); dialog.show(); dialog.raise_(); dialog.activateWindow()
