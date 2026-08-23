"""Owns the live Project document, selection, and reversible edit history."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import QObject, pyqtSignal

from opencae.model.core import Entity, EntityRef
from opencae.model.project import Project

from .commands import (
    ProjectCommand,
    make_add_command,
    make_delete_command,
    make_replace_command,
)
from .undo_entry import UndoEntry


class ProjectStore(QObject):
    """Transactional document store for user-authored Project mutations."""

    changed = pyqtSignal(str)
    scene_changed = pyqtSignal(str)
    selection_changed = pyqtSignal(object)
    active_part_changed = pyqtSignal(object)
    message = pyqtSignal(str)

    def __init__(self, project: Project | None = None):
        """Create a store around one valid Project document."""
        super().__init__()
        self.project = project or Project()
        self.project.ensure_references(strict=True)
        self._selection = None
        self.active_part_id = (
            self.project.parts[0].id if self.project.parts else None
        )
        self._undo: list[UndoEntry] = []
        self._redo: list[UndoEntry] = []

    @property
    def selection(self):
        """Return the current Entity selection resolved in the live graph."""
        if isinstance(self._selection, EntityRef):
            return self.project.try_resolve(self._selection)
        return self._selection

    @property
    def selection_id(self):
        """Return the selected Entity ID when selection is entity-backed."""
        return (
            self._selection.entity_id
            if isinstance(self._selection, EntityRef)
            else None
        )

    def active_part(self):
        """Return the active Part or ``None`` when the Project has no Parts."""
        if not self.active_part_id:
            return None
        return next(
            (
                part
                for part in self.project.parts
                if part.id == self.active_part_id
            ),
            None,
        )

    def set_active_part(self, part_id):
        """Select an existing Project Part as active."""
        if part_id is not None and not any(
            part.id == part_id for part in self.project.parts
        ):
            raise ValueError(f"Part '{part_id}' does not exist in this Project")
        if part_id == self.active_part_id:
            return
        self.active_part_id = part_id
        self.active_part_changed.emit(self.active_part())

    def execute(self, description: str, command: ProjectCommand):
        """Apply one command atomically and record it only after validation."""
        self.project.ensure_references(strict=True)
        snapshot = deepcopy(self.project)
        active_before = self.active_part_id
        selected_before = self.selection_id

        try:
            self.project = command.apply(self.project)
            self.project.ensure_references(strict=True)
            self._repair_active_part()
            selected_after = (
                selected_before
                if selected_before in self.project.index.by_id
                else None
            )
        except Exception:
            self._restore_snapshot(snapshot, active_before, selected_before)
            raise

        self._undo.append(
            UndoEntry(
                description,
                command,
                active_before,
                self.active_part_id,
                selected_before,
                selected_after,
            )
        )
        self._redo.clear()
        self._restore_selection(selected_after)
        self.changed.emit(description)
        self.message.emit(description)

    def add_entity(
        self,
        description: str,
        parent_id: str,
        attribute: str,
        entity: Entity,
    ):
        """Insert one Entity through a transactional command."""
        self.execute(
            description,
            make_add_command(self.project, parent_id, attribute, entity),
        )

    def replace_entity(
        self,
        description: str,
        parent_id: str,
        attribute: str,
        entity: Entity,
    ):
        """Replace one Entity while preserving its immutable ID."""
        self.execute(
            description,
            make_replace_command(self.project, parent_id, attribute, entity),
        )

    def delete_entity(
        self,
        description: str,
        parent_id: str,
        attribute: str,
        entity_id: str,
    ):
        """Delete one Entity through a reversible command."""
        self.execute(
            description,
            make_delete_command(
                self.project,
                parent_id,
                attribute,
                entity_id,
            ),
        )

    def invalidate_scene(self, reason="Model display changed"):
        """Notify viewport consumers that rendered model data changed."""
        self.scene_changed.emit(reason)

    def replace(self, project, description="Project loaded"):
        """Atomically replace the whole document with one valid Project."""
        project.ensure_references(strict=True)
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
        """Select a live Project Entity or a non-Entity UI selection value."""
        if isinstance(entity, Entity):
            if entity is not self.project and self.project.try_resolve(entity.id) is not entity:
                raise ValueError(
                    f"{type(entity).__name__} '{entity.name}' does not belong "
                    "to this Project"
                )
            self._selection = EntityRef.of(entity)
        else:
            self._selection = entity
        self.selection_changed.emit(self.selection)

    def undo(self):
        """Undo the latest successful user edit."""
        self._apply_history(self._undo, self._redo, False, "Undo")

    def redo(self):
        """Redo the latest successfully undone user edit."""
        self._apply_history(self._redo, self._undo, True, "Redo")

    def _apply_history(self, source, target, forward, prefix):
        """Move one history entry only after its mutation succeeds."""
        if not source:
            return
        entry = source[-1]
        snapshot = deepcopy(self.project)
        active_before_attempt = self.active_part_id
        selected_before_attempt = self.selection_id

        try:
            self.project = (
                entry.command.apply(self.project)
                if forward
                else entry.command.undo(self.project)
            )
            self.project.ensure_references(strict=True)
        except Exception:
            self._restore_snapshot(
                snapshot,
                active_before_attempt,
                selected_before_attempt,
            )
            raise

        source.pop()
        target.append(entry)
        self.active_part_id = (
            entry.active_after if forward else entry.active_before
        )
        self._repair_active_part()
        selected_id = (
            entry.selected_after if forward else entry.selected_before
        )
        self._restore_selection(selected_id)
        self.changed.emit(f"{prefix}: {entry.description}")
        self.scene_changed.emit(prefix)

    def _restore_snapshot(self, snapshot, active_id, selected_id):
        """Restore the exact pre-attempt graph and UI identity state."""
        snapshot.ensure_references(strict=False)
        self.project = snapshot
        self.active_part_id = active_id
        self._repair_active_part()
        self._selection = (
            EntityRef(selected_id)
            if selected_id and selected_id in self.project.index.by_id
            else None
        )

    def _restore_selection(self, entity_id):
        """Restore an Entity selection by stable ID in the current graph."""
        self._selection = (
            EntityRef(entity_id)
            if entity_id and entity_id in self.project.index.by_id
            else None
        )
        self.selection_changed.emit(self.selection)

    def _repair_active_part(self):
        """Move active-part state to a valid Part after graph changes."""
        previous = self.active_part_id
        if self.active_part() is None:
            self.active_part_id = (
                self.project.parts[0].id if self.project.parts else None
            )
        changed = previous != self.active_part_id
        if changed:
            self.active_part_changed.emit(self.active_part())
        return changed
