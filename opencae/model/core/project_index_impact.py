"""Classify whether model values can change ProjectIndex ownership or references."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from .persistent_model_field import is_project_index_field


def value_affects_project_index(value: Any, _active: set[int] | None = None) -> bool:
    """Return whether ``value`` can contain an Entity or EntityRef relationship.

    The check is structural rather than size-based. Dataclass fields explicitly
    excluded from ProjectIndex traversal are skipped, which keeps this operation
    constant-time for compact mesh records whose large arrays are pure numeric
    payloads.
    """
    if value is None:
        return False

    # Local imports avoid an Entity <-> impact-classifier import cycle while
    # retaining exact type checks for the two graph-bearing leaf types.
    from .entity import Entity
    from .reference import EntityRef

    if isinstance(value, (Entity, EntityRef)):
        return True
    if not is_dataclass(value) and not isinstance(value, (list, tuple, dict)):
        return False

    active = _active if _active is not None else set()
    identity = id(value)
    if identity in active:
        return False
    active.add(identity)
    try:
        if is_dataclass(value):
            return any(
                value_affects_project_index(getattr(value, info.name), active)
                for info in fields(value)
                if is_project_index_field(info)
            )
        if isinstance(value, (list, tuple)):
            return any(value_affects_project_index(item, active) for item in value)
        return any(value_affects_project_index(item, active) for item in value.values())
    finally:
        active.remove(identity)
