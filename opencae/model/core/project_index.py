from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Iterable

from .entity import Entity
from .reference import EntityRef


@dataclass(frozen=True, slots=True)
class ReferenceUse:
    source_id: str
    source_name: str
    field_path: str
    expected_type: str = ""


class ProjectIndex:
    """Runtime identity index for one project aggregate."""

    def __init__(self, project):
        self.project = project
        self.by_id: dict[str, Entity] = {}
        self.parent_id: dict[str, str | None] = {}
        self.path: dict[str, str] = {}
        self.reverse: dict[str, list[ReferenceUse]] = {}
        self._build()

    def _build(self):
        self._visit_entity(self.project, None, "project")
        for entity in self.by_id.values():
            entity._bind_project(self.project)
        for entity in self.by_id.values():
            self._scan_references(entity)

    def _visit_entity(self, entity: Entity, parent_id: str | None, path: str):
        existing = self.by_id.get(entity.id)
        if existing is not None and existing is not entity:
            raise ValueError(
                f"Duplicate entity id '{entity.id}' at {path} and {self.path[entity.id]}"
            )
        self.by_id[entity.id] = entity
        self.parent_id[entity.id] = parent_id
        self.path[entity.id] = path
        for field_info in fields(entity):
            if field_info.name.startswith("_"):
                continue
            self._visit_value(
                getattr(entity, field_info.name),
                entity.id,
                f"{path}.{field_info.name}",
            )

    def _visit_value(self, value: Any, parent_id: str, path: str):
        if isinstance(value, Entity):
            self._visit_entity(value, parent_id, path)
            return
        if is_dataclass(value):
            for field_info in fields(value):
                self._visit_value(
                    getattr(value, field_info.name),
                    parent_id,
                    f"{path}.{field_info.name}",
                )
            return
        if isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                self._visit_value(item, parent_id, f"{path}[{index}]")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                self._visit_value(item, parent_id, f"{path}[{key!r}]")

    def _scan_references(self, source: Entity):
        def walk(value: Any, path: str):
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
                return
            if is_dataclass(value):
                for item in fields(value):
                    walk(getattr(value, item.name), f"{path}.{item.name}")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")
            elif isinstance(value, dict):
                for key, item in value.items():
                    walk(item, f"{path}[{key!r}]")
            elif isinstance(value, tuple):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")

        for field_info in fields(source):
            if field_info.name.startswith("_"):
                continue
            walk(getattr(source, field_info.name), field_info.name)

    def resolve(
        self,
        ref: EntityRef | str | None,
        expected_type: type | tuple[type, ...] | None = None,
    ):
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
                f"Entity '{entity.name}' is {type(entity).__name__}, expected {names}"
            )
        return entity

    def try_resolve(
        self,
        ref: EntityRef | str | None,
        expected_type: type | tuple[type, ...] | None = None,
    ):
        try:
            return self.resolve(ref, expected_type)
        except (KeyError, TypeError):
            return None

    def references_to(self, entity_id: str) -> tuple[ReferenceUse, ...]:
        return tuple(self.reverse.get(entity_id, ()))

    def children_of(self, entity_id: str) -> tuple[Entity, ...]:
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
        return (
            self.by_id.values()
            if accepted is None
            else (item for item in self.by_id.values() if isinstance(item, accepted))
        )
