from __future__ import annotations
from copy import deepcopy
from PyQt6.QtWidgets import QDialog

from opencae.model.geometry import GeometryFeature,PartitionEdgeFeature,PartitionFaceFeature,PartitionPlaneFeature
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
        dialog=PartitionDialog(self.ctx.selected_labels,self.ctx.selected_points,feature,self.ctx.parent); self._dialogs.append(dialog)
        dialog.accepted.connect(lambda d=dialog,pid=part.id,fid=getattr(feature,'id',None):self._apply(d,pid,fid)); dialog.finished.connect(lambda _code,d=dialog:self._dialogs.remove(d) if d in self._dialogs else None); dialog.show(); dialog.raise_(); dialog.activateWindow()
    def _apply(self,dialog,part_id,feature_id):
        part=next((p for p in self.ctx.store.project.parts if p.id==part_id),None)
        if part is None:return
        values=dialog.values(); candidate=deepcopy(part); existing=next((f for f in candidate.geometry if f.id==feature_id),None)
        cls={'Cell by plane':PartitionPlaneFeature,'Face by two points':PartitionFaceFeature,'Edge at parameter':PartitionEdgeFeature,'Edge at vertex':PartitionEdgeFeature}[values['partition_type']]
        feature=cls(name=values['name'],references=values['references'],parameters=values['parameters'])
        if existing is None:candidate.geometry.append(feature)
        else:
            index=candidate.geometry.index(existing); feature.id=existing.id; feature.suppressed=existing.suppressed; candidate.geometry[index]=feature
        candidate.mesh.status='Outdated'
        if self.ctx.validate_geometry(candidate,'Partition failed'):self.ctx.replace_part(candidate,f"{'Edited' if existing else 'Created'} {feature.name}")
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
