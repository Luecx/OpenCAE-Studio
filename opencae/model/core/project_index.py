"""Build runtime identity, ownership, path, and reverse-reference indexes."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Iterable

from .entity import Entity
from .persistent_model_field import (
    is_owned_model_field,
    is_project_index_field,
    is_reference_model_field,
    reference_type_for_field,
)
from .reference import EntityRef
from .reference_type import matches_reference_type
from .reference_use import ReferenceUse


class ProjectIndex:
    """Runtime identity and relationship index for one Project aggregate.

    Ownership and relationships are deliberately distinct. An owned field is
    traversed to discover child Entities; a field carrying ``reference_type``
    points at an already-owned Entity object and is only entered into the reverse
    relationship index.
    """

    def __init__(self, project):
        self.project = project
        self.by_id: dict[str, Entity] = {}
        self.parent_id: dict[str, str | None] = {}
        self.path: dict[str, str] = {}
        self.reverse: dict[str, list[ReferenceUse]] = {}
        self._active_values: set[int] = set()
        self._build()

    def _build(self) -> None:
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
        existing = self.by_id.get(entity.id)
        if existing is entity:
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
            if not is_owned_model_field(field_info):
                continue
            self._visit_value(
                getattr(entity, field_info.name),
                entity.id,
                f"{path}.{field_info.name}",
            )

    def _visit_value(self, value: Any, parent_id: str, path: str) -> None:
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
                    if not is_owned_model_field(field_info):
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
        """Record direct object relationships nested inside one source Entity."""
        active_values: set[int] = set()

        def record(value: Any, path: str, expected_type: str) -> None:
            if value is None:
                return
            if isinstance(value, EntityRef):
                if value.entity_id:
                    self.reverse.setdefault(value.entity_id, []).append(
                        ReferenceUse(
                            source.id,
                            source.name,
                            path,
                            value.expected_type or expected_type,
                        )
                    )
                return
            if isinstance(value, Entity):
                self.reverse.setdefault(value.id, []).append(
                    ReferenceUse(source.id, source.name, path, expected_type)
                )
                return
            if isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    record(item, f"{path}[{index}]", expected_type)
                return
            if isinstance(value, dict):
                for key, item in value.items():
                    record(item, f"{path}[{key!r}]", expected_type)

        def walk(value: Any, path: str) -> None:
            if isinstance(value, Entity):
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
                        if not is_project_index_field(item):
                            continue
                        child = getattr(value, item.name)
                        child_path = f"{path}.{item.name}"
                        if is_reference_model_field(item):
                            record(
                                child,
                                child_path,
                                reference_type_for_field(item),
                            )
                        elif is_owned_model_field(item):
                            walk(child, child_path)
                elif isinstance(value, (list, tuple)):
                    for index, item in enumerate(value):
                        walk(item, f"{path}[{index}]")
                else:
                    for key, item in value.items():
                        walk(item, f"{path}[{key!r}]")
            finally:
                active_values.remove(identity)

        for field_info in fields(source):
            if not is_project_index_field(field_info):
                continue
            value = getattr(source, field_info.name)
            if is_reference_model_field(field_info):
                record(
                    value,
                    field_info.name,
                    reference_type_for_field(field_info),
                )
            elif is_owned_model_field(field_info):
                walk(value, field_info.name)

    def resolve(
        self,
        ref: EntityRef | Entity | str | None,
        expected_type: type | tuple[type, ...] | str | None = None,
    ):
        """Resolve a persistence ref, object, or ID and enforce type contracts."""
        if isinstance(ref, Entity):
            entity = self.by_id.get(ref.id)
            if entity is not ref:
                raise KeyError(
                    f"Entity '{ref.id}' is not the canonical object in this Project"
                )
        else:
            entity_id = ref.entity_id if isinstance(ref, EntityRef) else str(ref or "")
            entity = self.by_id.get(entity_id)
            if entity is None:
                raise KeyError(f"Referenced entity '{entity_id}' does not exist")

        if isinstance(ref, EntityRef) and ref.expected_type:
            if not matches_reference_type(entity, ref.expected_type):
                raise TypeError(
                    f"Entity '{entity.name}' is {type(entity).__name__}, "
                    f"expected {ref.expected_type}"
                )

        if isinstance(expected_type, str):
            if not matches_reference_type(entity, expected_type):
                raise TypeError(
                    f"Entity '{entity.name}' is {type(entity).__name__}, "
                    f"expected {expected_type}"
                )
        elif expected_type is not None and not isinstance(entity, expected_type):
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
        ref: EntityRef | Entity | str | None,
        expected_type: type | tuple[type, ...] | str | None = None,
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
            else (
                item
                for item in self.by_id.values()
                if isinstance(item, accepted)
            )
        )
