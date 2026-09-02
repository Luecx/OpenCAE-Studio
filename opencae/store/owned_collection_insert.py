"""Defines ownership-transferring insertion for large detached Entities."""

from __future__ import annotations

from dataclasses import dataclass

from opencae.model.core import Entity

from .commands import ProjectCommand, _collection, _require_index


@dataclass
class OwnedCollectionInsertCommand(ProjectCommand):
    """Move one detached Entity between an owner collection and undo history.

    The caller transfers exclusive ownership of ``entity`` to this command. On
    apply the exact object is inserted into the Project; on undo the same object
    is removed again and retained by the history entry. This avoids redundant
    copies for large imported or duplicated Parts while preserving reversible
    ownership semantics.
    """

    parent_id: str
    attribute: str
    entity: Entity
    index: int | None = None

    def is_atomic(self) -> bool:
        """Insertion mutates only after all address/identity checks succeed."""
        return True

    def affects_project_index(self, project) -> bool:
        """Owned Entity insertion always changes graph ownership."""
        return True

    def apply(self, project):
        """Insert the command-owned Entity without copying it."""
        if self.entity.id in project.index.by_id:
            raise ValueError(
                f"Entity '{self.entity.id}' already exists in the Project graph"
            )
        collection = _collection(project, self.parent_id, self.attribute)
        position = (
            len(collection)
            if self.index is None
            else min(max(int(self.index), 0), len(collection))
        )
        collection.insert(position, self.entity)
        self.index = position
        project.invalidate_index()
        return project

    def undo(self, project):
        """Remove the inserted Entity and keep the exact object for redo."""
        collection = _collection(project, self.parent_id, self.attribute)
        position = _require_index(collection, self.entity.id, self.attribute)
        stored = collection.pop(position)
        if stored is not self.entity:
            # Identity should be stable because the store owns the live graph.
            # Preserve the actual live object if an external caller replaced it.
            self.entity = stored
        self.index = position
        project.invalidate_index()
        return project
