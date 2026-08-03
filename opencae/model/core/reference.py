from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from .model_registry import register_model_type

T = TypeVar("T")


@register_model_type("entity_ref")
@dataclass(frozen=True, slots=True)
class EntityRef(Generic[T]):
    entity_id: str = ""
    expected_type: str = ""
    legacy_name: str = ""

    @property
    def is_bound(self) -> bool:
        return bool(self.entity_id)

    def bound_to(self, entity) -> "EntityRef[T]":
        return EntityRef(entity.id, self.expected_type or type(entity).__name__, "")

    @classmethod
    def of(cls, entity, expected_type: str = "") -> "EntityRef":
        if entity is None: return cls(expected_type=expected_type)
        if isinstance(entity, EntityRef): return entity
        if hasattr(entity, "id"): return cls(str(entity.id), expected_type or type(entity).__name__)
        return cls(expected_type=expected_type, legacy_name=str(entity))


def as_entity_ref(value, expected_type: str = "") -> EntityRef:
    if value is None: return EntityRef(expected_type=expected_type)
    if isinstance(value, EntityRef):
        if expected_type and not value.expected_type:
            return EntityRef(value.entity_id, expected_type, value.legacy_name)
        return value
    return EntityRef.of(value, expected_type)
