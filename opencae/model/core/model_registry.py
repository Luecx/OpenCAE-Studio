from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T", bound=type)
MODEL_TYPES: dict[str, type] = {}


def register_model_type(type_name: str) -> Callable[[T], T]:
    def decorate(cls: T) -> T:
        cls.model_type = type_name
        MODEL_TYPES[type_name] = cls
        return cls
    return decorate


def model_class(type_name: str) -> type:
    try:
        return MODEL_TYPES[type_name]
    except KeyError as exc:
        raise ValueError(f"Unknown model type: {type_name}") from exc
