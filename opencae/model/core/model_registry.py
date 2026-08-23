"""Registers polymorphic model classes used by persistence decoding."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from .object_reference_aliases import install_object_reference_aliases

T = TypeVar("T", bound=type)
MODEL_TYPES: dict[str, type] = {}


def register_model_type(type_name: str) -> Callable[[T], T]:
    """Return a decorator registering one model class under ``type_name``."""
    def decorate(cls: T) -> T:
        """Register the class and install its public object-reference aliases."""
        cls.model_type = type_name
        MODEL_TYPES[type_name] = cls
        install_object_reference_aliases(cls)
        return cls

    return decorate


def model_class(type_name: str) -> type:
    """Return the registered class for one persisted model type name."""
    try:
        return MODEL_TYPES[type_name]
    except KeyError as exc:
        raise ValueError(f"Unknown model type: {type_name}") from exc
