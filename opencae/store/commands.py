"""Defines reversible, ID-addressed mutations of the persistent Project graph."""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
from typing import Any

from opencae.model.core import Entity
from opencae.model.core.persistent_model_field import is_persistent_model_field


class ProjectCommand(ABC):
    """A reversible mutation of the current Project graph."""

    @abstractmethod
    def apply(self, project):
        """Apply this mutation and return the mutated Project."""
        raise NotImplementedError

    @abstractmethod
    def undo(self, project):
        """Reverse this mutation and return the mutated Project."""
        raise NotImplementedError


@dataclass(frozen=True)
class CompositeCommand(ProjectCommand):
    """Apply several commands as one atomic logical mutation."""

    commands: tuple[ProjectCommand, ...]

    def apply(self, project):
        """Apply all children, rolling back already-applied children on failure."""
        applied: list[ProjectCommand] = []
        try:
            for command in self.commands:
                project = command.apply(project)
                applied.append(command)
                # Later children may address entities added/replaced by earlier
                # children. Reindex without enforcing final-state invariants yet.
                project.rebuild_index(strict=False)
            project.ensure_references(strict=True)
            return project
        except Exception:
            _rollback_applied(project, applied)
            raise

    def undo(self, project):
        """Undo all children atomically, restoring them if one undo fails."""
        undone: list[ProjectCommand] = []
        try:
            for command in reversed(self.commands):
                project = command.undo(project)
                undone.append(command)
                project.rebuild_index(strict=False)
            project.ensure_references(strict=True)
            return project
        except Exception:
            _restore_undone(project, undone)
            raise


@dataclass(frozen=True)
class CollectionInsertCommand(ProjectCommand):
    """Insert one owned Entity into a persistent list."""

    parent_id: str
    attribute: str
    entity: Entity
    index: int | None = None

    def apply(self, project):
        """Insert the entity after enforcing global ID uniqueness."""
        project.rebuild_index(strict=False)
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
        collection.insert(position, deepcopy(self.entity))
        project.invalidate_index()
        return project

    def undo(self, project):
        """Remove the entity previously inserted by this command."""
        collection = _collection(project, self.parent_id, self.attribute)
        index = _require_index(collection, self.entity.id, self.attribute)
        del collection[index]
        project.invalidate_index()
        return project


@dataclass(frozen=True)
class CollectionReplaceCommand(ProjectCommand):
    """Replace one Entity while preserving immutable identity."""

    parent_id: str
    attribute: str
    before: Entity
    after: Entity

    def __post_init__(self):
        """Reject replacements that would change persistent identity."""
        if self.before.id != self.after.id:
            raise ValueError("Replacement entities must preserve their immutable id")

    def apply(self, project):
        """Replace the current entity with the recorded after-state."""
        collection = _collection(project, self.parent_id, self.attribute)
        index = _require_index(collection, self.before.id, self.attribute)
        collection[index] = deepcopy(self.after)
        project.invalidate_index()
        return project

    def undo(self, project):
        """Restore the recorded before-state."""
        collection = _collection(project, self.parent_id, self.attribute)
        index = _require_index(collection, self.after.id, self.attribute)
        collection[index] = deepcopy(self.before)
        project.invalidate_index()
        return project


@dataclass(frozen=True)
class CollectionDeleteCommand(ProjectCommand):
    """Delete one owned Entity and retain enough state for undo."""

    parent_id: str
    attribute: str
    entity: Entity
    index: int

    def apply(self, project):
        """Delete the addressed entity from its persistent owner list."""
        collection = _collection(project, self.parent_id, self.attribute)
        current = _require_index(collection, self.entity.id, self.attribute)
        del collection[current]
        project.invalidate_index()
        return project

    def undo(self, project):
        """Reinsert the deleted entity after enforcing global ID uniqueness."""
        project.rebuild_index(strict=False)
        if self.entity.id in project.index.by_id:
            raise ValueError(
                f"Entity '{self.entity.id}' already exists in the Project graph"
            )
        collection = _collection(project, self.parent_id, self.attribute)
        collection.insert(
            min(max(int(self.index), 0), len(collection)),
            deepcopy(self.entity),
        )
        project.invalidate_index()
        return project


@dataclass(frozen=True)
class UpdateFieldCommand(ProjectCommand):
    """Replace one persistent dataclass field on an Entity-owned path."""

    entity_id: str
    field_name: str
    before: Any
    after: Any

    def apply(self, project):
        """Apply the recorded field value."""
        owner, field_name = _field_owner(
            project.resolve(self.entity_id),
            self.field_name,
        )
        setattr(owner, field_name, deepcopy(self.after))
        project.invalidate_index()
        return project

    def undo(self, project):
        """Restore the previous field value."""
        owner, field_name = _field_owner(
            project.resolve(self.entity_id),
            self.field_name,
        )
        setattr(owner, field_name, deepcopy(self.before))
        project.invalidate_index()
        return project


def make_add_command(
    project,
    parent_id: str,
    attribute: str,
    entity: Entity,
) -> CollectionInsertCommand:
    """Create a list-insert command for the current collection position."""
    collection = _collection(project, parent_id, attribute)
    return CollectionInsertCommand(
        parent_id,
        attribute,
        deepcopy(entity),
        len(collection),
    )


def make_replace_command(
    project,
    parent_id: str,
    attribute: str,
    entity: Entity,
) -> CollectionReplaceCommand:
    """Create an identity-preserving replacement command."""
    collection = _collection(project, parent_id, attribute)
    index = _require_index(collection, entity.id, attribute)
    return CollectionReplaceCommand(
        parent_id,
        attribute,
        deepcopy(collection[index]),
        deepcopy(entity),
    )


def make_delete_command(
    project,
    parent_id: str,
    attribute: str,
    entity_id: str,
) -> CollectionDeleteCommand:
    """Create a reversible delete command for one owned Entity."""
    collection = _collection(project, parent_id, attribute)
    index = _require_index(collection, entity_id, attribute)
    return CollectionDeleteCommand(
        parent_id,
        attribute,
        deepcopy(collection[index]),
        index,
    )


def entity_collection_location(project, entity_id: str) -> tuple[str, str]:
    """Return ``(parent_id, persistent list path)`` for an indexed entity."""
    project.rebuild_index(strict=False)
    parent_id = project.index.parent_id.get(entity_id)
    if parent_id is None:
        raise ValueError(f"Entity '{entity_id}' has no deletable collection owner")
    entity_path = project.index.path.get(entity_id, "")
    parent_path = project.index.path.get(parent_id, "")
    prefix = f"{parent_path}."
    if not entity_path.startswith(prefix):
        raise ValueError(f"Cannot derive collection path for entity '{entity_id}'")
    relative = entity_path[len(prefix):]
    bracket = relative.rfind("[")
    if bracket < 0 or not relative.endswith("]"):
        raise ValueError(f"Entity '{entity_id}' is not stored in a persistent list")
    attribute = relative[:bracket]
    if not attribute:
        raise ValueError(f"Entity '{entity_id}' has an empty collection path")
    _collection(project, parent_id, attribute)
    return parent_id, attribute


def _collection(project, parent_id: str, attribute: str):
    """Resolve a persistent list path without allowing arbitrary attributes."""
    parent = project if parent_id == project.id else project.try_resolve(parent_id)
    if parent is None:
        raise ValueError(f"Command parent '{parent_id}' no longer exists")
    value = parent
    traversed: list[str] = []
    for component in attribute.split("."):
        traversed.append(component)
        value = _persistent_field_value(value, component, ".".join(traversed))
    if not isinstance(value, list):
        raise TypeError(
            f"{type(parent).__name__}.{attribute} is not a persistent list"
        )
    return value


def _persistent_field_value(owner, name: str, path: str):
    """Read one declared persistent dataclass field from ``owner``."""
    if not is_dataclass(owner):
        raise AttributeError(
            f"Cannot traverse non-dataclass value at persistent path '{path}'"
        )
    field_info = next((item for item in fields(owner) if item.name == name), None)
    if field_info is None or not is_persistent_model_field(field_info):
        raise AttributeError(
            f"{type(owner).__name__} has no persistent field '{name}'"
        )
    return getattr(owner, name)


def _find_index(collection, entity_id: str) -> int | None:
    """Return the index of ``entity_id`` inside one Entity collection."""
    return next(
        (
            index
            for index, item in enumerate(collection)
            if getattr(item, "id", None) == entity_id
        ),
        None,
    )


def _require_index(collection, entity_id: str, attribute: str) -> int:
    """Return an Entity collection index or raise for a stale command."""
    index = _find_index(collection, entity_id)
    if index is None:
        raise ValueError(f"Entity '{entity_id}' no longer exists in {attribute}")
    return index


def _field_owner(entity, field_path: str):
    """Resolve and validate one persistent field path for UpdateFieldCommand."""
    parts = field_path.split(".")
    if not parts or any(not item for item in parts):
        raise ValueError("Field path must contain persistent field names")
    owner = entity
    for index, component in enumerate(parts[:-1], start=1):
        owner = _persistent_field_value(
            owner,
            component,
            ".".join(parts[:index]),
        )
    final = parts[-1]
    _persistent_field_value(owner, final, field_path)
    return owner, final


def _rollback_applied(project, applied: list[ProjectCommand]) -> None:
    """Best-effort rollback for a failed CompositeCommand.apply()."""
    rollback_error = None
    for command in reversed(applied):
        try:
            project = command.undo(project)
            project.rebuild_index(strict=False)
        except Exception as exc:  # pragma: no cover - catastrophic invariant break
            rollback_error = exc
            break
    if rollback_error is not None:
        raise RuntimeError("Composite command rollback failed") from rollback_error
    project.ensure_references(strict=False)


def _restore_undone(project, undone: list[ProjectCommand]) -> None:
    """Best-effort restoration for a failed CompositeCommand.undo()."""
    rollback_error = None
    for command in reversed(undone):
        try:
            project = command.apply(project)
            project.rebuild_index(strict=False)
        except Exception as exc:  # pragma: no cover - catastrophic invariant break
            rollback_error = exc
            break
    if rollback_error is not None:
        raise RuntimeError("Composite undo rollback failed") from rollback_error
    project.ensure_references(strict=False)
