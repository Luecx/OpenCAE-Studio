from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from opencae.model.core import Entity, EntityRef
from opencae.model.project import Project
from opencae.persistence.project_codec import project_from_dict, project_to_dict
from .json_patch import apply, changes
from .undo_entry import UndoEntry


class ProjectStore(QObject):
    changed=pyqtSignal(str); scene_changed=pyqtSignal(str); selection_changed=pyqtSignal(object)
    active_part_changed=pyqtSignal(object); message=pyqtSignal(str)

    def __init__(self, project: Project | None = None):
        super().__init__(); self.project=project or Project(); self._selection=None
        self.active_part_id=self.project.parts[0].id if self.project.parts else None
        self._undo:list[UndoEntry]=[]; self._redo:list[UndoEntry]=[]

    @property
    def selection(self):
        if isinstance(self._selection, EntityRef): return self.project.try_resolve(self._selection)
        return self._selection

    @property
    def selection_id(self): return self._selection.entity_id if isinstance(self._selection, EntityRef) else None

    def active_part(self): return self.project.index.by_id.get(self.active_part_id) if self.active_part_id else None

    def set_active_part(self, part_id):
        if part_id==self.active_part_id:return
        self.active_part_id=part_id; self.active_part_changed.emit(self.active_part())

    def mutate(self, description: str, operation: Callable[[Project], None]):
        before=project_to_dict(self.project); active_before=self.active_part_id; selected_before=self.selection_id
        operation(self.project); self.project.ensure_references(strict=False); self._repair_active_part(); after=project_to_dict(self.project)
        patch=changes(before,after)
        if patch:self._undo.append(UndoEntry(description,patch,active_before,self.active_part_id)); self._redo.clear()
        self._restore_selection(selected_before); self.changed.emit(description); self.message.emit(description)

    def invalidate_scene(self,reason="Model display changed"): self.scene_changed.emit(reason)

    def replace(self,project,description="Project loaded"):
        project.ensure_references(strict=False); self.project=project; self._undo.clear(); self._redo.clear(); self._selection=None
        self.active_part_id=project.parts[0].id if project.parts else None
        self.changed.emit(description); self.selection_changed.emit(None); self.active_part_changed.emit(self.active_part()); self.message.emit(description)

    def select(self,entity):
        self._selection = EntityRef.of(entity) if isinstance(entity, Entity) else entity
        self.selection_changed.emit(self.selection)

    def undo(self): self._apply_history(self._undo,self._redo,False,"Undo")
    def redo(self): self._apply_history(self._redo,self._undo,True,"Redo")

    def _apply_history(self,source,target,forward,prefix):
        if not source:return
        selected_id=self.selection_id; entry=source.pop(); encoded=project_to_dict(self.project); self.project=project_from_dict(apply(encoded,entry.patch,forward)); target.append(entry)
        self.active_part_id=entry.active_after if forward else entry.active_before; self._repair_active_part(); self._restore_selection(selected_id)
        self.changed.emit(f"{prefix}: {entry.description}"); self.scene_changed.emit(prefix)

    def _restore_selection(self, entity_id):
        self._selection = EntityRef(entity_id) if entity_id and entity_id in self.project.index.by_id else None
        self.selection_changed.emit(self.selection)

    def _repair_active_part(self):
        previous=self.active_part_id
        if self.active_part() is None:self.active_part_id=self.project.parts[0].id if self.project.parts else None
        changed=previous!=self.active_part_id
        if changed:self.active_part_changed.emit(self.active_part())
        return changed
