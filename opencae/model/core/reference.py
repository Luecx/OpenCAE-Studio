"""Defines stable ID-only references between persistent OpenCAE entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from .model_registry import register_model_type

T = TypeVar("T")


@register_model_type("entity_ref")
@dataclass(frozen=True, slots=True)
class EntityRef(Generic[T]):
    """Persistent reference to one Entity by immutable ID and type contract."""

    entity_id: str = ""
    expected_type: str = ""

    @property
    def is_bound(self) -> bool:
        """Return whether this reference contains an entity ID."""
        return bool(self.entity_id)

    def bound_to(self, entity) -> "EntityRef[T]":
        """Return this reference bound to ``entity`` while preserving its type."""
        return EntityRef.of(entity, self.expected_type)

    @classmethod
    def of(cls, entity, expected_type: str = "") -> "EntityRef":
        """Create a stable reference from an Entity or existing EntityRef.

        Display names and arbitrary strings are intentionally rejected. Runtime
        authoring relationships are object-based; raw IDs are only constructed
        explicitly through ``EntityRef(entity_id, expected_type)``.
        """
        if entity is None:
            return cls(expected_type=expected_type)
        if isinstance(entity, EntityRef):
            if expected_type and not entity.expected_type:
                return cls(entity.entity_id, expected_type)
            return entity

        from .entity import Entity

        if not isinstance(entity, Entity):
            raise TypeError(
                "EntityRef.of() expects an Entity object or EntityRef, "
                f"got {type(entity).__name__}"
            )
        return cls(str(entity.id), expected_type or type(entity).__name__)


def as_entity_ref(value, expected_type: str = "") -> EntityRef:
    """Normalize an Entity/EntityRef/None value to a strict EntityRef."""
    if value is None:
        return EntityRef(expected_type=expected_type)
    if isinstance(value, EntityRef):
        if expected_type and not value.expected_type:
            return EntityRef(value.entity_id, expected_type)
        return value
    return EntityRef.of(value, expected_type)
