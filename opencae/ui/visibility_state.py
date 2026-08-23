"""Session-level entity and topology visibility state with scoped invalidation signals."""

from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import QObject, pyqtSignal


_TOPOLOGY_KINDS = {"faces", "cells", "elements"}


class VisibilityState(QObject):
    """Session-level display state shared by the tree, ribbon and viewport.

    Visibility is deliberately not part of the analysis model. Hiding an object
    or topology entity changes only the viewport and project-tree presentation;
    it never suppresses geometry, removes mesh members or changes solver decks.
    Scoped signals let the viewport update existing actors for topology edits
    instead of treating every visibility change as a full scene invalidation.
    """

    changed = pyqtSignal()
    entity_changed = pyqtSignal(str)
    topology_changed = pyqtSignal(str, str)
    reset = pyqtSignal()

    def __init__(self, project=None, parent=None):
        super().__init__(parent)
        self._project_id = str(getattr(project, "id", "") or "")
        self._hidden_entities: set[str] = set()
        self._hidden_topology: dict[tuple[str, str], set[int]] = {}

    def sync_project(self, project) -> None:
        """Drop stale session state when another project replaces the current one."""
        project_id = str(getattr(project, "id", "") or "")
        if project_id == self._project_id:
            return
        self._project_id = project_id
        self._hidden_entities.clear()
        self._hidden_topology.clear()
        self.reset.emit()
        self.changed.emit()

    def is_entity_visible(self, entity_or_id) -> bool:
        """Return whether one model entity is currently visible."""
        entity_id = _entity_id(entity_or_id)
        return not entity_id or entity_id not in self._hidden_entities

    def set_entity_visible(self, entity_or_id, visible: bool) -> None:
        """Set one entity's visibility and emit an entity-scoped invalidation."""
        entity_id = _entity_id(entity_or_id)
        if not entity_id:
            return
        before = entity_id in self._hidden_entities
        if visible:
            self._hidden_entities.discard(entity_id)
        else:
            self._hidden_entities.add(entity_id)
        after = entity_id in self._hidden_entities
        if before != after:
            self.entity_changed.emit(entity_id)
            self.changed.emit()

    def toggle_entity(self, entity_or_id) -> bool:
        """Toggle one entity and return its resulting visibility."""
        visible = self.is_entity_visible(entity_or_id)
        self.set_entity_visible(entity_or_id, not visible)
        return not visible

    def hidden_topology(self, owner_id: str, kind: str) -> frozenset[int]:
        """Return hidden topology ids for one Part and canonical category."""
        key = self._topology_key(owner_id, kind)
        return frozenset(self._hidden_topology.get(key, ()))

    def set_hidden_topology(
        self,
        owner_id: str,
        kind: str,
        values: Iterable[int],
    ) -> None:
        """Replace one hidden-topology set and emit only its scoped invalidation."""
        key = self._topology_key(owner_id, kind)
        normalized = {int(value) for value in values}
        before = self._hidden_topology.get(key, set())
        if normalized == before:
            return
        if normalized:
            self._hidden_topology[key] = normalized
        else:
            self._hidden_topology.pop(key, None)
        self.topology_changed.emit(*key)
        self.changed.emit()

    def hide_topology(self, owner_id: str, kind: str, values: Iterable[int]) -> None:
        """Add topology ids to the hidden set."""
        current = set(self.hidden_topology(owner_id, kind))
        current.update(int(value) for value in values)
        self.set_hidden_topology(owner_id, kind, current)

    def show_topology(self, owner_id: str, kind: str, values: Iterable[int]) -> None:
        """Remove topology ids from the hidden set."""
        current = set(self.hidden_topology(owner_id, kind))
        current.difference_update(int(value) for value in values)
        self.set_hidden_topology(owner_id, kind, current)

    def invert_topology(self, owner_id: str, kind: str, universe: Iterable[int]) -> None:
        """Invert hidden state over the supplied topology universe."""
        values = {int(value) for value in universe}
        hidden = set(self.hidden_topology(owner_id, kind))
        self.set_hidden_topology(owner_id, kind, values - hidden)

    def show_all_topology(self, owner_id: str, kind: str) -> None:
        """Make every topology member of one category visible."""
        self.set_hidden_topology(owner_id, kind, ())

    def hide_all_topology(
        self,
        owner_id: str,
        kind: str,
        universe: Iterable[int],
    ) -> None:
        """Hide every topology member in the supplied universe."""
        self.set_hidden_topology(owner_id, kind, universe)

    @staticmethod
    def _topology_key(owner_id: str, kind: str) -> tuple[str, str]:
        owner = str(owner_id or "")
        category = str(kind or "").strip().lower()
        aliases = {
            "face": "faces",
            "cell": "cells",
            "element": "elements",
        }
        category = aliases.get(category, category)
        if not owner:
            raise ValueError("Visibility topology requires an owner id")
        if category not in _TOPOLOGY_KINDS:
            raise ValueError(f"Unsupported visibility topology kind: {kind}")
        return owner, category


def _entity_id(value) -> str:
    """Normalize an entity object or raw id to the session visibility key."""
    return str(getattr(value, "id", value) or "")
