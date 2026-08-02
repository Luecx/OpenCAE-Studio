from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import QObject,pyqtSignal
from opencae.model.project import Project
from opencae.persistence.project_codec import project_from_dict,project_to_dict
from .json_patch import apply,changes
from .undo_entry import UndoEntry

class ProjectStore(QObject):
    changed=pyqtSignal(str); scene_changed=pyqtSignal(str); selection_changed=pyqtSignal(object)
    active_part_changed=pyqtSignal(object); message=pyqtSignal(str)
    def __init__(self,project:Project|None=None):
        super().__init__(); self.project=project or Project(); self.selection=None
        self.active_part_id=self.project.parts[0].id if self.project.parts else None
        self._undo:list[UndoEntry]=[]; self._redo:list[UndoEntry]=[]
    def active_part(self):return next((p for p in self.project.parts if p.id==self.active_part_id),None)
    def set_active_part(self,part_id):
        if part_id==self.active_part_id:return
        self.active_part_id=part_id; self.active_part_changed.emit(self.active_part())
    def mutate(self,description:str,operation:Callable[[Project],None]):
        before=project_to_dict(self.project); active_before=self.active_part_id
        operation(self.project); self._repair_active_part(); after=project_to_dict(self.project)
        patch=changes(before,after)
        if patch:self._undo.append(UndoEntry(description,patch,active_before,self.active_part_id)); self._redo.clear()
        self.changed.emit(description); self.message.emit(description)
    def invalidate_scene(self,reason="Model display changed"):self.scene_changed.emit(reason)
    def replace(self,project,description="Project loaded"):
        self.project=project; self._undo.clear(); self._redo.clear(); self.selection=None
        self.active_part_id=project.parts[0].id if project.parts else None
        self.changed.emit(description); self.selection_changed.emit(None); self.active_part_changed.emit(self.active_part()); self.message.emit(description)
    def select(self,entity):self.selection=entity; self.selection_changed.emit(entity)
    def undo(self):self._apply_history(self._undo,self._redo,False,"Undo")
    def redo(self):self._apply_history(self._redo,self._undo,True,"Redo")
    def _apply_history(self,source,target,forward,prefix):
        if not source:return
        entry=source.pop(); encoded=project_to_dict(self.project); self.project=project_from_dict(apply(encoded,entry.patch,forward)); target.append(entry)
        self.active_part_id=entry.active_after if forward else entry.active_before; self.selection=None; self._repair_active_part()
        self.selection_changed.emit(None); self.changed.emit(f"{prefix}: {entry.description}"); self.scene_changed.emit(prefix)
    def _repair_active_part(self):
        previous=self.active_part_id
        if self.active_part() is None:self.active_part_id=self.project.parts[0].id if self.project.parts else None
        changed=previous!=self.active_part_id
        if changed:self.active_part_changed.emit(self.active_part())
        return changed
