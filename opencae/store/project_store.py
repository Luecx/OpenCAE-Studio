from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from opencae.model.core import Entity, EntityRef
from opencae.model.project import Project
from .commands import (
    ProjectCommand, make_add_command, make_delete_command,
    make_replace_command,
)
from .undo_entry import UndoEntry


class ProjectStore(QObject):
    changed = pyqtSignal(str)
    scene_changed = pyqtSignal(str)
    selection_changed = pyqtSignal(object)
    active_part_changed = pyqtSignal(object)
    message = pyqtSignal(str)

    def __init__(self, project: Project | None = None):
        super().__init__()
        self.project = project or Project()
        self._selection = None
        self.active_part_id = self.project.parts[0].id if self.project.parts else None
        self._undo: list[UndoEntry] = []
        self._redo: list[UndoEntry] = []

    @property
    def selection(self):
        if isinstance(self._selection, EntityRef):
            return self.project.try_resolve(self._selection)
        return self._selection

    @property
    def selection_id(self):
        return self._selection.entity_id if isinstance(self._selection, EntityRef) else None

    def active_part(self):
        return self.project.index.by_id.get(self.active_part_id) if self.active_part_id else None

    def set_active_part(self, part_id):
        if part_id == self.active_part_id:
            return
        self.active_part_id = part_id
        self.active_part_changed.emit(self.active_part())

    def execute(self, description: str, command: ProjectCommand):
        active_before = self.active_part_id
        selected_before = self.selection_id
        self.project = command.apply(self.project)
        self.project.ensure_references(strict=False)
        self._repair_active_part()
        selected_after = selected_before if selected_before in self.project.index.by_id else None
        self._undo.append(UndoEntry(
            description, command, active_before, self.active_part_id,
            selected_before, selected_after,
        ))
        self._redo.clear()
        self._restore_selection(selected_after)
        self.changed.emit(description)
        self.message.emit(description)

    def add_entity(self, description: str, parent_id: str, attribute: str, entity: Entity):
        self.execute(description, make_add_command(self.project, parent_id, attribute, entity))

    def replace_entity(self, description: str, parent_id: str, attribute: str, entity: Entity):
        self.execute(description, make_replace_command(self.project, parent_id, attribute, entity))

    def delete_entity(self, description: str, parent_id: str, attribute: str, entity_id: str):
        self.execute(description, make_delete_command(self.project, parent_id, attribute, entity_id))

    def invalidate_scene(self, reason="Model display changed"):
        self.scene_changed.emit(reason)

    def replace(self, project, description="Project loaded"):
        project.ensure_references(strict=False)
        self.project = project
        self._undo.clear()
        self._redo.clear()
        self._selection = None
        self.active_part_id = project.parts[0].id if project.parts else None
        self.changed.emit(description)
        self.selection_changed.emit(None)
        self.active_part_changed.emit(self.active_part())
        self.message.emit(description)

    def select(self, entity):
        self._selection = EntityRef.of(entity) if isinstance(entity, Entity) else entity
        self.selection_changed.emit(self.selection)

    def undo(self):
        self._apply_history(self._undo, self._redo, False, "Undo")

    def redo(self):
        self._apply_history(self._redo, self._undo, True, "Redo")

    def _apply_history(self, source, target, forward, prefix):
        if not source:
            return
        entry = source.pop()
        self.project = entry.command.apply(self.project) if forward else entry.command.undo(self.project)
        self.project.ensure_references(strict=False)
        target.append(entry)
        self.active_part_id = entry.active_after if forward else entry.active_before
        self._repair_active_part()
        selected_id = entry.selected_after if forward else entry.selected_before
        self._restore_selection(selected_id)
        self.changed.emit(f"{prefix}: {entry.description}")
        self.scene_changed.emit(prefix)

    def _restore_selection(self, entity_id):
        self._selection = EntityRef(entity_id) if entity_id and entity_id in self.project.index.by_id else None
        self.selection_changed.emit(self.selection)

    def _repair_active_part(self):
        previous = self.active_part_id
        if self.active_part() is None:
            self.active_part_id = self.project.parts[0].id if self.project.parts else None
        changed = previous != self.active_part_id
        if changed:
            self.active_part_changed.emit(self.active_part())
        return changed
