"""Builds runtime identity, ownership, path, and reverse-reference indexes."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Iterable

from .entity import Entity
from .persistent_model_field import is_persistent_model_field
from .reference import EntityRef
from .reference_use import ReferenceUse


class ProjectIndex:
    """Runtime identity and reference index for one Project aggregate."""

    def __init__(self, project):
        """Index all reachable entities and references in ``project``."""
        self.project = project
        self.by_id: dict[str, Entity] = {}
        self.parent_id: dict[str, str | None] = {}
        self.path: dict[str, str] = {}
        self.reverse: dict[str, list[ReferenceUse]] = {}
        self._active_values: set[int] = set()
        self._build()

    def _build(self) -> None:
        """Populate ownership first, then bind entities and scan references."""
        self._visit_entity(self.project, None, "project")
        for entity in self.by_id.values():
            entity._bind_project(self.project)
        for entity in self.by_id.values():
            self._scan_references(entity)

    def _visit_entity(
        self,
        entity: Entity,
        parent_id: str | None,
        path: str,
    ) -> None:
        """Register one Entity and recursively traverse its owned values."""
        existing = self.by_id.get(entity.id)
        if existing is entity:
            # An object alias is a relationship to the already indexed entity,
            # not another ownership path to traverse recursively.
            return
        if existing is not None and existing is not entity:
            raise ValueError(
                f"Duplicate entity id '{entity.id}' at {path} and "
                f"{self.path[entity.id]}"
            )

        self.by_id[entity.id] = entity
        self.parent_id[entity.id] = parent_id
        self.path[entity.id] = path
        for field_info in fields(entity):
            if not is_persistent_model_field(field_info):
                continue
            self._visit_value(
                getattr(entity, field_info.name),
                entity.id,
                f"{path}.{field_info.name}",
            )

    def _visit_value(self, value: Any, parent_id: str, path: str) -> None:
        """Traverse nested dataclasses/containers to discover owned Entities."""
        if isinstance(value, Entity):
            self._visit_entity(value, parent_id, path)
            return
        if not is_dataclass(value) and not isinstance(
            value,
            (list, tuple, dict),
        ):
            return

        identity = id(value)
        if identity in self._active_values:
            return
        self._active_values.add(identity)
        try:
            if is_dataclass(value):
                for field_info in fields(value):
                    if not is_persistent_model_field(field_info):
                        continue
                    self._visit_value(
                        getattr(value, field_info.name),
                        parent_id,
                        f"{path}.{field_info.name}",
                    )
            elif isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    self._visit_value(item, parent_id, f"{path}[{index}]")
            else:
                for key, item in value.items():
                    self._visit_value(item, parent_id, f"{path}[{key!r}]")
        finally:
            self._active_values.remove(identity)

    def _scan_references(self, source: Entity) -> None:
        """Record every EntityRef nested inside one source Entity."""
        active_values: set[int] = set()

        def walk(value: Any, path: str) -> None:
            """Recursively collect reference leaves without crossing Entities."""
            if isinstance(value, EntityRef):
                if value.entity_id:
                    self.reverse.setdefault(value.entity_id, []).append(
                        ReferenceUse(
                            source.id,
                            source.name,
                            path,
                            value.expected_type,
                        )
                    )
                return
            if isinstance(value, Entity):
                # Owned entities are scanned independently, otherwise their
                # references would be attributed to the wrong source object.
                return
            if not is_dataclass(value) and not isinstance(
                value,
                (list, tuple, dict),
            ):
                return

            identity = id(value)
            if identity in active_values:
                return
            active_values.add(identity)
            try:
                if is_dataclass(value):
                    for item in fields(value):
                        if is_persistent_model_field(item):
                            walk(
                                getattr(value, item.name),
                                f"{path}.{item.name}",
                            )
                elif isinstance(value, (list, tuple)):
                    for index, item in enumerate(value):
                        walk(item, f"{path}[{index}]")
                else:
                    for key, item in value.items():
                        walk(item, f"{path}[{key!r}]")
            finally:
                active_values.remove(identity)

        for field_info in fields(source):
            if not is_persistent_model_field(field_info):
                continue
            walk(getattr(source, field_info.name), field_info.name)

    def resolve(
        self,
        ref: EntityRef | str | None,
        expected_type: type | tuple[type, ...] | None = None,
    ):
        """Resolve a stable reference/ID and optionally enforce a Python type."""
        entity_id = ref.entity_id if isinstance(ref, EntityRef) else str(ref or "")
        entity = self.by_id.get(entity_id)
        if entity is None:
            raise KeyError(f"Referenced entity '{entity_id}' does not exist")
        if expected_type is not None and not isinstance(entity, expected_type):
            names = (
                ", ".join(item.__name__ for item in expected_type)
                if isinstance(expected_type, tuple)
                else expected_type.__name__
            )
            raise TypeError(
                f"Entity '{entity.name}' is {type(entity).__name__}, "
                f"expected {names}"
            )
        return entity

    def try_resolve(
        self,
        ref: EntityRef | str | None,
        expected_type: type | tuple[type, ...] | None = None,
    ):
        """Resolve a reference or return ``None`` for missing/wrong-type values."""
        try:
            return self.resolve(ref, expected_type)
        except (KeyError, TypeError):
            return None

    def references_to(self, entity_id: str) -> tuple[ReferenceUse, ...]:
        """Return all recorded reverse references targeting ``entity_id``."""
        return tuple(self.reverse.get(entity_id, ()))

    def children_of(self, entity_id: str) -> tuple[Entity, ...]:
        """Return structurally owned child Entities of ``entity_id``."""
        return tuple(
            entity
            for child_id, entity in self.by_id.items()
            if self.parent_id.get(child_id) == entity_id
        )

    def find(
        self,
        name: str,
        accepted: type | tuple[type, ...] | None = None,
        parent_id: str | None = None,
    ) -> list[Entity]:
        """Find entities by display name with optional type/parent filtering."""
        text = str(name or "").casefold()
        result = []
        for entity in self.by_id.values():
            if entity.name.casefold() != text:
                continue
            if accepted is not None and not isinstance(entity, accepted):
                continue
            if parent_id is not None and self.parent_id.get(entity.id) != parent_id:
                continue
            result.append(entity)
        return result

    def entities(
        self,
        accepted: type | tuple[type, ...] | None = None,
    ) -> Iterable[Entity]:
        """Iterate all indexed entities, optionally restricted by type."""
        return (
            self.by_id.values()
            if accepted is None
            else (
                item
                for item in self.by_id.values()
                if isinstance(item, accepted)
            )
        )
