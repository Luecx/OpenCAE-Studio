"""Validates object identity and ownership for the public Model facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opencae.model.core import Entity

if TYPE_CHECKING:
    from .model import Model


def require_owned(
    model: "Model",
    entity: Entity,
    expected: type | tuple[type, ...],
) -> Entity:
    """Return ``entity`` after verifying type and membership in ``model``."""
    if not isinstance(entity, expected):
        names = (
            ", ".join(item.__name__ for item in expected)
            if isinstance(expected, tuple)
            else expected.__name__
        )
        raise TypeError(f"Expected {names}, got {type(entity).__name__}")
    if entity is model.project:
        return entity
    # Identity matters: a copied entity with the same ID is still another graph.
    if model.project.try_resolve(entity.id) is not entity:
        raise ValueError(
            f"{type(entity).__name__} '{entity.name}' does not belong to this Model"
        )
    return entity
