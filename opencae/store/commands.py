from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from opencae.model.core import Entity


class ProjectCommand(ABC):
    """A reversible mutation of a project graph.

    Commands resolve their target collection on every execution. They never keep
    live entity objects from a previous project graph, which makes them safe
    across undo/redo and project-index rebuilds.
    """

    @abstractmethod
    def apply(self, project):
        raise NotImplementedError

    @abstractmethod
    def undo(self, project):
        raise NotImplementedError


@dataclass(frozen=True)
class CompositeCommand(ProjectCommand):
    commands: tuple[ProjectCommand, ...]

    def apply(self, project):
        for command in self.commands:
            project = command.apply(project)
            project.rebuild_index(strict=False)
        return project

    def undo(self, project):
        for command in reversed(self.commands):
            project = command.undo(project)
            project.rebuild_index(strict=False)
        return project


@dataclass(frozen=True)
class CollectionInsertCommand(ProjectCommand):
    parent_id: str
    attribute: str
    entity: Entity
    index: int | None = None

    def apply(self, project):
        collection = _collection(project, self.parent_id, self.attribute)
        if _find_index(collection, self.entity.id) is not None:
            raise ValueError(f"Entity '{self.entity.id}' already exists in {self.attribute}")
        position = len(collection) if self.index is None else min(max(int(self.index), 0), len(collection))
        collection.insert(position, deepcopy(self.entity))
        return project

    def undo(self, project):
        collection = _collection(project, self.parent_id, self.attribute)
        index = _require_index(collection, self.entity.id, self.attribute)
        del collection[index]
        return project


@dataclass(frozen=True)
class CollectionReplaceCommand(ProjectCommand):
    parent_id: str
    attribute: str
    before: Entity
    after: Entity

    def __post_init__(self):
        if self.before.id != self.after.id:
            raise ValueError("Replacement entities must preserve their immutable id")

    def apply(self, project):
        collection = _collection(project, self.parent_id, self.attribute)
        index = _require_index(collection, self.before.id, self.attribute)
        collection[index] = deepcopy(self.after)
        return project

    def undo(self, project):
        collection = _collection(project, self.parent_id, self.attribute)
        index = _require_index(collection, self.after.id, self.attribute)
        collection[index] = deepcopy(self.before)
        return project


@dataclass(frozen=True)
class CollectionDeleteCommand(ProjectCommand):
    parent_id: str
    attribute: str
    entity: Entity
    index: int

    def apply(self, project):
        collection = _collection(project, self.parent_id, self.attribute)
        current = _require_index(collection, self.entity.id, self.attribute)
        del collection[current]
        return project

    def undo(self, project):
        collection = _collection(project, self.parent_id, self.attribute)
        if _find_index(collection, self.entity.id) is not None:
            raise ValueError(f"Entity '{self.entity.id}' already exists in {self.attribute}")
        collection.insert(min(max(int(self.index), 0), len(collection)), deepcopy(self.entity))
        return project


@dataclass(frozen=True)
class UpdateFieldCommand(ProjectCommand):
    entity_id: str
    field_name: str
    before: Any
    after: Any

    def apply(self, project):
        owner, field_name = _field_owner(project.resolve(self.entity_id), self.field_name)
        setattr(owner, field_name, deepcopy(self.after))
        return project

    def undo(self, project):
        owner, field_name = _field_owner(project.resolve(self.entity_id), self.field_name)
        setattr(owner, field_name, deepcopy(self.before))
        return project


def make_add_command(project, parent_id: str, attribute: str, entity: Entity) -> CollectionInsertCommand:
    collection = _collection(project, parent_id, attribute)
    return CollectionInsertCommand(parent_id, attribute, deepcopy(entity), len(collection))


def make_replace_command(project, parent_id: str, attribute: str, entity: Entity) -> CollectionReplaceCommand:
    collection = _collection(project, parent_id, attribute)
    index = _require_index(collection, entity.id, attribute)
    return CollectionReplaceCommand(parent_id, attribute, deepcopy(collection[index]), deepcopy(entity))


def make_delete_command(project, parent_id: str, attribute: str, entity_id: str) -> CollectionDeleteCommand:
    collection = _collection(project, parent_id, attribute)
    index = _require_index(collection, entity_id, attribute)
    return CollectionDeleteCommand(parent_id, attribute, deepcopy(collection[index]), index)



def entity_collection_location(project, entity_id: str) -> tuple[str, str]:
    """Return ``(parent_id, persistent list path)`` for an indexed entity.

    The project index records paths such as ``project.parts[0].mesh.seeds[2]``.
    Commands need the stable owning entity ID plus the list path relative to
    that owner, for example ``(part.id, "mesh.seeds")``.
    """
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
    parent = project if parent_id == project.id else project.try_resolve(parent_id)
    if parent is None:
        raise ValueError(f"Command parent '{parent_id}' no longer exists")
    value = parent
    for component in attribute.split("."):
        value = getattr(value, component, None)
        if value is None:
            raise AttributeError(f"{type(parent).__name__} has no persistent path '{attribute}'")
    if not isinstance(value, list):
        raise TypeError(f"{type(parent).__name__}.{attribute} is not a persistent list")
    return value


def _find_index(collection, entity_id: str) -> int | None:
    return next((index for index, item in enumerate(collection) if getattr(item, "id", None) == entity_id), None)


def _require_index(collection, entity_id: str, attribute: str) -> int:
    index = _find_index(collection, entity_id)
    if index is None:
        raise ValueError(f"Entity '{entity_id}' no longer exists in {attribute}")
    return index


def _field_owner(entity, field_path: str):
    parts = field_path.split(".")
    owner = entity
    for component in parts[:-1]:
        owner = getattr(owner, component)
    return owner, parts[-1]
