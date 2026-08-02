from __future__ import annotations
from copy import deepcopy
from PyQt6.QtWidgets import QDialog

from opencae.model.datums import create_datum
from opencae.model.entities.datums import DatumPlane
from opencae.model.geometry import GeometryFeature,PartitionEdgeFeature,PartitionFaceFeature,PartitionPlaneFeature
from opencae.model.naming import next_name
from opencae.ui.dialogs.datum_plane import DatumPlaneDialog
from opencae.ui.dialogs.partition import PartitionDialog

class PartPartitions:
    def __init__(self,context):self.ctx=context; self._dialogs=[]
    def partition(self):
        part=self.ctx.active_part()
        if not self.ctx.require_geometry(part):return
        self._open_dialog(part)
    def edit_partition(self,feature):
        part=self.ctx.active_part()
        if part:self._open_dialog(part,feature)
    def _open_dialog(self,part,feature=None):
        datum_planes=[item for item in getattr(part,'datums',()) if isinstance(item,DatumPlane)]
        dialog=PartitionDialog(self.ctx.selected_labels,self.ctx.selected_points,feature,self.ctx.parent,datum_planes,lambda owner,done,pid=part.id:self._create_datum_plane(pid,owner,done)); self._dialogs.append(dialog)
        slot=lambda _value,d=dialog:d.update_selection()
        self.ctx.store.selection_changed.connect(slot)
        dialog.accepted.connect(lambda d=dialog,pid=part.id,fid=getattr(feature,'id',None):self._apply(d,pid,fid))
        dialog.finished.connect(lambda _code,d=dialog,s=slot:self._finish_dialog(d,s)); dialog.show(); dialog.raise_(); dialog.activateWindow()
    def _finish_dialog(self,dialog,slot):
        try:self.ctx.store.selection_changed.disconnect(slot)
        except Exception:pass
        if dialog in self._dialogs:self._dialogs.remove(dialog)
    def _apply(self,dialog,part_id,feature_id):
        part=next((p for p in self.ctx.store.project.parts if p.id==part_id),None)
        if part is None:return
        values=dialog.values(); candidate=deepcopy(part); existing=next((f for f in candidate.geometry if f.id==feature_id),None)
        cls={'Cell by plane':PartitionPlaneFeature,'Face by two points':PartitionFaceFeature,'Edge at parameter':PartitionEdgeFeature,'Edge at vertex':PartitionEdgeFeature}[values['partition_type']]
        feature=cls(name=values['name'],id=existing.id if existing else None,references=values['references'],parameters=values['parameters']) if existing else cls(name=values['name'],references=values['references'],parameters=values['parameters'])
        if existing is None:candidate.geometry.append(feature)
        else:
            index=candidate.geometry.index(existing); feature.suppressed=existing.suppressed; candidate.geometry[index]=feature
        candidate.mesh.status='Outdated'
        if self.ctx.validate_geometry(candidate,'Partition failed'):self.ctx.replace_part(candidate,f"{'Edited' if existing else 'Created'} {feature.name}")
    def _create_datum_plane(self,part_id,owner,done):
        part=next((item for item in self.ctx.store.project.parts if item.id==part_id),None)
        if part is None:return
        dialog=DatumPlaneDialog(next_name("Datum Plane",part.datums),[item.name for item in part.datums],part.coordinate_systems,owner or self.ctx.parent)
        dialog.pick_requested.connect(lambda allowed,callback:self.ctx.parent.viewport.begin_context_pick(allowed,callback))
        dialog.preview_requested.connect(self.ctx.parent.viewport.show_datum_preview)
        def apply(values):
            current=next((item for item in self.ctx.store.project.parts if item.id==part_id),None)
            if current is None:return
            datum=create_datum(values["kind"],values["name"],values["method"],values["parameters"])
            self.ctx.store.mutate(f"Created {datum.name}",lambda _project:current.datums.append(datum))
            self.ctx.store.select(datum); self.ctx.store.invalidate_scene("Datum updated"); done(datum); dialog.close()
        dialog.apply_requested.connect(apply)
        dialog.finished.connect(lambda _code:self.ctx.parent.viewport.hide_datum_preview())
        dialog.show(); dialog.raise_(); dialog.activateWindow()
    def rebuild_geometry(self):
        part=self.ctx.active_part()
        if self.ctx.require_geometry(part) and self.ctx.validate_geometry(deepcopy(part),'Geometry rebuild failed'):self.ctx.store.invalidate_scene(f'Rebuilt geometry for {part.name}'); self.ctx.store.message.emit(f'Rebuilt geometry for {part.name}')
    def suppress_feature(self):
        part=self.ctx.active_part(); selected=self.ctx.store.selection; feature=selected if isinstance(selected,GeometryFeature) else None
        if feature is None and part:feature=next((item for item in reversed(part.geometry) if not item.feature_type.startswith('Imported')),None)
        if part is None or feature is None:self.ctx.store.message.emit('Select a partition feature first'); return
        if feature.feature_type.startswith('Imported'):self.ctx.store.message.emit('The source geometry feature cannot be suppressed'); return
        candidate,target=self.ctx.feature_copy(feature); target.suppressed=not target.suppressed; candidate.mesh.status='Outdated'
        if self.ctx.validate_geometry(candidate,'Feature update failed'):self.ctx.replace_part(candidate,f"{'Resumed' if not target.suppressed else 'Suppressed'} {target.name}")
