"""Multi-document facade over the canonical single-project ProjectStore."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from PyQt6.QtCore import pyqtSignal

from opencae.model.project import Project

from .project_store import ProjectStore


@dataclass
class _ProjectSession:
    project: Project
    selection: object
    active_part_id: str | None
    undo: list
    redo: list
    reusable_placeholder: bool = False


class MultiProjectStore(ProjectStore):
    """Keep independent ProjectStore state for multiple open documents.

    Existing controllers intentionally continue to receive one stable store object.
    Switching a project only rebinds the active Project/selection/history tuple and
    emits the same signals a full document replacement already used, so the tree,
    ribbon, viewport, and dialogs do not need a second multi-document code path.
    """

    projects_changed = pyqtSignal()
    active_project_changed = pyqtSignal(int)

    def __init__(self, project: Project | None = None):
        super().__init__(project)
        self._sessions = [self._capture_session()]
        self._sessions[0].reusable_placeholder = project is None
        self._active_project_index = 0

    @property
    def projects(self) -> tuple[Project, ...]:
        self._sync_active_session()
        return tuple(session.project for session in self._sessions)

    @property
    def active_project_index(self) -> int:
        return self._active_project_index

    def is_placeholder_project(self, index: int) -> bool:
        """Return whether an open slot is only the reusable empty startup document."""
        index = int(index)
        if index < 0 or index >= len(self._sessions):
            return False
        self._sync_active_session()
        return self._is_placeholder(self._sessions[index])

    def add_project(
        self,
        project: Project,
        description: str = "Project opened",
        *,
        reuse_placeholder: bool = True,
    ) -> int:
        """Open ``project`` as a new document and make it active."""
        project.ensure_references(strict=True)
        self._sync_active_session()
        replacing_placeholder = bool(
            reuse_placeholder
            and self._is_placeholder(self._sessions[self._active_project_index])
        )
        self._reject_identity_overlap(project, skip_active=replacing_placeholder)
        if replacing_placeholder:
            self.project = project
            self._selection = None
            self.active_part_id = project.parts[0].id if project.parts else None
            self._undo = []
            self._redo = []
            self._sync_active_session()
            self._sessions[self._active_project_index].reusable_placeholder = False
            self.projects_changed.emit()
            self._emit_project_switch(description)
            return self._active_project_index

        session = _ProjectSession(
            project=project,
            selection=None,
            active_part_id=project.parts[0].id if project.parts else None,
            undo=[],
            redo=[],
        )
        self._sessions.append(session)
        index = len(self._sessions) - 1
        self.projects_changed.emit()
        self.set_active_project(index, description=description)
        return index

    def set_active_project(self, index: int, *, description: str | None = None) -> None:
        """Activate one open document while preserving every other session's state."""
        index = int(index)
        if index < 0 or index >= len(self._sessions):
            raise IndexError(f"Project index out of range: {index}")
        if index == self._active_project_index:
            return
        self._sync_active_session()
        self._active_project_index = index
        self._bind_session(self._sessions[index])
        self._emit_project_switch(
            description or f"Switched to {self.project.name}"
        )

    def close_project(self, index: int) -> bool:
        """Close one document, leaving a reusable empty placeholder when it was last."""
        index = int(index)
        if index < 0 or index >= len(self._sessions):
            return False

        self._sync_active_session()
        if len(self._sessions) == 1:
            if self._is_placeholder(self._sessions[0]):
                return False
            project = Project()
            self.project = project
            self._selection = None
            self.active_part_id = None
            self._undo = []
            self._redo = []
            self._sessions[0] = self._capture_session()
            self._sessions[0].reusable_placeholder = True
            self._active_project_index = 0
            self.projects_changed.emit()
            self._emit_project_switch("Closed project")
            return True

        active_session = self._sessions[self._active_project_index]
        closing_active = index == self._active_project_index
        self._sessions.pop(index)

        if closing_active:
            self._active_project_index = min(index, len(self._sessions) - 1)
            self._bind_session(self._sessions[self._active_project_index])
            self.projects_changed.emit()
            self._emit_project_switch(f"Switched to {self.project.name}")
            return True

        self._active_project_index = self._sessions.index(active_session)
        self.projects_changed.emit()
        self.active_project_changed.emit(self._active_project_index)
        return True

    def project_for_entity(self, entity_or_id) -> Project | None:
        """Return the open Project owning an entity id, including inactive documents."""
        entity_id = str(getattr(entity_or_id, "id", entity_or_id) or "")
        if not entity_id:
            return None
        self._sync_active_session()
        for session in self._sessions:
            if session.project.try_resolve(entity_id) is not None:
                return session.project
        return None

    def resolve_any(self, entity_or_id):
        """Resolve an entity across all open Projects without changing the active one."""
        project = self.project_for_entity(entity_or_id)
        return project.try_resolve(entity_or_id) if project is not None else None

    def add_entity(self, description, parent_id, attribute, entity):
        with self._session_for_entity(parent_id):
            return super().add_entity(description, parent_id, attribute, entity)

    def replace_entity(self, description, parent_id, attribute, entity):
        with self._session_for_entity(parent_id):
            return super().replace_entity(description, parent_id, attribute, entity)

    def delete_entity(self, description, parent_id, attribute, entity_id):
        with self._session_for_entity(parent_id):
            return super().delete_entity(description, parent_id, attribute, entity_id)

    def update_runtime_fields(self, entity_id, changes):
        with self._session_for_entity(entity_id):
            return super().update_runtime_fields(entity_id, changes)

    def _session_for_entity_index(self, entity_or_id) -> int | None:
        entity_id = str(getattr(entity_or_id, "id", entity_or_id) or "")
        if not entity_id:
            return None
        self._sync_active_session()
        for index, session in enumerate(self._sessions):
            if session.project.try_resolve(entity_id) is not None:
                return index
        return None

    @contextmanager
    def _session_for_entity(self, entity_or_id):
        target = self._session_for_entity_index(entity_or_id)
        if target is None or target == self._active_project_index:
            yield
            return

        active_index = self._active_project_index
        active_signals_blocked = self.signalsBlocked()
        self._sync_active_session()
        self._bind_session(self._sessions[target])
        self.blockSignals(True)
        try:
            yield
        finally:
            self._sync_session(target)
            self._bind_session(self._sessions[active_index])
            self.blockSignals(active_signals_blocked)

    def _capture_session(self) -> _ProjectSession:
        return _ProjectSession(
            project=self.project,
            selection=self._selection,
            active_part_id=self.active_part_id,
            undo=self._undo,
            redo=self._redo,
        )

    def _sync_active_session(self) -> None:
        if not hasattr(self, "_sessions"):
            return
        self._sync_session(self._active_project_index)

    def _sync_session(self, index: int) -> None:
        session = self._sessions[index]
        session.project = self.project
        session.selection = self._selection
        session.active_part_id = self.active_part_id
        session.undo = self._undo
        session.redo = self._redo

    def _bind_session(self, session: _ProjectSession) -> None:
        self.project = session.project
        self._selection = session.selection
        self.active_part_id = session.active_part_id
        self._undo = session.undo
        self._redo = session.redo

    def _emit_project_switch(self, description: str) -> None:
        self.changed.emit(str(description))
        self.selection_changed.emit(self.selection)
        self.active_part_changed.emit(self.active_part())
        self.scene_changed.emit("Project switched")
        self.active_project_changed.emit(self._active_project_index)
        self.message.emit(str(description))

    def _reject_identity_overlap(self, project: Project, *, skip_active: bool) -> None:
        """Reject documents whose persistent entity ids collide with an open document."""
        incoming = set(project.index.by_id)
        for index, session in enumerate(self._sessions):
            if skip_active and index == self._active_project_index:
                continue
            overlap = incoming.intersection(session.project.index.by_id)
            if overlap:
                raise ValueError(
                    "This project shares persistent entity identities with an "
                    "already open project. Close the other copy before opening it."
                )

    @staticmethod
    def _is_placeholder(session: _ProjectSession) -> bool:
        if not session.reusable_placeholder:
            return False
        project = session.project
        if session.undo or session.redo or project.path is not None:
            return False
        if project.name != "Untitled":
            return False
        collections = (
            project.parts,
            project.supports,
            project.loads,
            project.amplitudes,
            project.materials,
            project.sections,
            project.profiles,
            project.fields,
            project.steps,
            project.analyses,
            project.studies,
            project.jobs,
            project.results,
        )
        return not any(collections) and not tuple(project.assembly.instances)
