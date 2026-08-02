from PyQt6.QtWidgets import QDialog

from opencae.model.assembly import Instance, create_constraint
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

class AssemblyController:
    def __init__(self,store,parent,part_controller=None):
        self.store=store; self.parent=parent; self.part_controller=part_controller; self.regions=AssemblyRegions(self); self._dialogs=[]
    def _create_part(self,parent=None):
        before={part.id for part in self.store.project.parts}; self.part_controller.new_part(parent=parent); created=next((part for part in self.store.project.parts if part.id not in before),None); return created.name if created else None
    def add_instance(self):
        project=self.store.project; dialog=InstanceDialog([p.name for p in project.parts],self._create_part,[i.name for i in project.assembly.instances],self.parent,next_name("Instance",project.assembly.instances))
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        v=dialog.values(); instance=Instance(name=v['name'],part_name=v['part_name']); self.store.mutate(f"Added instance {instance.name}",lambda p:p.assembly.instances.append(instance)); self.store.invalidate_scene("Assembly instance added")
    def duplicate_instance(self):
        if not self.store.project.assembly.instances:return
        src=self.store.project.assembly.instances[-1]; name=next_name(src.part_name,self.store.project.assembly.instances); self.store.mutate(f"Duplicated {src.name}",lambda p:p.assembly.instances.append(Instance(name=name,part_name=src.part_name,translation=src.translation,rotation=src.rotation))); self.store.invalidate_scene("Assembly instance duplicated")
    def transform(self):
        v=get_values(TransformInstanceDialog([i.name for i in self.store.project.assembly.instances],self.parent)); instance=next((i for i in self.store.project.assembly.instances if i.name==v['instance_name']),None) if v else None
        if not instance:return
        attr='translation' if v['operation']=='Translate' else 'rotation'; values=(v['x'],v['y'],v['z']); self.store.mutate(f"{v['operation']} {instance.name}",lambda p:setattr(instance,attr,values)); self.store.invalidate_scene("Assembly instance transformed")
    def suppress_instance(self):
        if self.store.project.assembly.instances:
            i=self.store.project.assembly.instances[-1]; self.store.mutate(f"Suppressed {i.name}",lambda p:setattr(i,'suppressed',not i.suppressed)); self.store.invalidate_scene("Assembly instance visibility changed")
    def _selection_labels(self):
        s=self.store.selection; items=s.get('entities',[s]) if isinstance(s,dict) else []; return [i.get('name') for i in items if i.get('name')]
    def node_set(self):self.regions.node_set()
    def element_set(self):self.regions.element_set()
    def surface(self):self.regions.surface()
    def coordinate_system(self):
        v=get_values(CoordinateSystemDialog(next_name("CSYS",self.store.project.assembly.coordinate_systems),[i.name for i in self.store.project.assembly.coordinate_systems],self.parent))
        if v:self.store.mutate(f"Created assembly {v['name']}",lambda p:p.assembly.coordinate_systems.append(CoordinateSystem(name=v['name'],system_type=v['system_type'],origin=v['origin'],axis_1=v['axis_1'],axis_2=v['axis_2'],scope='Assembly'))); self.store.invalidate_scene('Assembly coordinate system created')
    def reference_point(self):
        v=get_values(ReferencePointDialog(next_name("RP",self.store.project.assembly.reference_points),[i.name for i in self.store.project.assembly.reference_points],self.parent))
        if v:self.store.mutate(f"Created assembly {v['name']}",lambda p:p.assembly.reference_points.append(ReferencePoint(name=v['name'],position=(v['x'],v['y'],v['z']),scope='Assembly')))
    def constraint(self,constraint_type="Kinematic Coupling"):self._constraint_dialog(constraint_type)
    def edit_constraint(self,constraint):self._constraint_dialog(constraint.constraint_type,constraint)
    def _constraint_dialog(self,constraint_type,constraint=None):
        project=self.store.project; masters=[ConstraintReference(r.name,ConstraintReferenceKind.REFERENCE_POINT) for r in project.assembly.reference_points]
        slaves=[*(ConstraintReference(r.name,ConstraintReferenceKind.NODE_SET) for r in project.assembly.node_sets),*(ConstraintReference(r.name,ConstraintReferenceKind.ELEMENT_SET) for r in project.assembly.element_sets),*(ConstraintReference(r.name,ConstraintReferenceKind.SURFACE) for r in project.assembly.surfaces)]
        def create_master(owner=None):
            values=get_values(ReferencePointDialog(next_name("RP",project.assembly.reference_points),[i.name for i in project.assembly.reference_points],owner or self.parent))
            if not values:return None
            point=ReferencePoint(name=values['name'],position=(values['x'],values['y'],values['z']),scope='Assembly'); self.store.mutate(f"Created assembly {point.name}",lambda p:p.assembly.reference_points.append(point)); return point.name
        dialog=ConstraintDialog(masters,slaves,create_master,lambda owner,done:self._nested_surface(owner,done),self.parent,next_name(str(constraint_type).replace(" Coupling",""),project.assembly.constraints),[i.name for i in project.assembly.constraints],constraint_type,constraint); dialog.setModal(False); self._dialogs.append(dialog)
        def accepted():
            values=dialog.values(); kind=values.pop('constraint_type'); replacement=create_constraint(kind,**values)
            if constraint is None:self.store.mutate(f"Created {replacement.name}",lambda p:p.assembly.constraints.append(replacement))
            else:self.store.mutate(f"Edited {replacement.name}",lambda p:p.assembly.constraints.__setitem__(p.assembly.constraints.index(constraint),replacement))
        dialog.accepted.connect(accepted); dialog.finished.connect(lambda _code:self._dialogs.remove(dialog) if dialog in self._dialogs else None); dialog.show(); dialog.raise_(); dialog.activateWindow()
    def _nested_surface(self,owner,done):
        owner.hide(); dialog=SurfaceDialog(selection_provider=self._selection_labels,default_name=next_name("SURFACE",self.store.project.assembly.surfaces),existing_names=[i.name for i in self.store.project.assembly.surfaces],parent=self.parent); previous=self.parent.viewport.selection_mode; self.parent.viewport.set_selection_mode(dialog.mode()); slot=lambda _value:dialog.update_selection(); self.store.selection_changed.connect(slot)
        def restore():
            try:self.store.selection_changed.disconnect(slot)
            except Exception:pass
            self.parent.viewport.set_selection_mode(previous); owner.show(); owner.raise_(); owner.activateWindow()
        def commit(values):
            region=create_region("Surface",scope="Assembly",**values); self.store.mutate(f"Created assembly {region.name}",lambda p:p.assembly.surfaces.append(region)); done(region.name); dialog.close()
        dialog.selection_mode.currentTextChanged.connect(lambda _text:self.parent.viewport.set_selection_mode(dialog.mode())); dialog.committed.connect(commit); dialog.finished.connect(lambda _code:restore()); dialog.show(); dialog.raise_(); dialog.activateWindow()
