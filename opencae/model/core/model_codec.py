from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from enum import Enum
from typing import Any

from .model_registry import model_class


def encode_model(value: Any) -> Any:
    if is_dataclass(value):
        type_name = getattr(type(value), "model_type", None)
        data = {field.name: encode_model(getattr(value, field.name)) for field in fields(value) if field.init and field.metadata.get("serialize", True)}
        return {"__type__": type_name, **data} if type_name else data
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return {"__path__": str(value)}
    if isinstance(value, tuple):
        return {"__tuple__": [encode_model(item) for item in value]}
    if isinstance(value, list):
        return [encode_model(item) for item in value]
    if isinstance(value, dict):
        return {key: encode_model(item) for key, item in value.items()}
    return value


def decode_model(value: Any) -> Any:
    if isinstance(value, list):
        return [decode_model(item) for item in value]
    if not isinstance(value, dict):
        return value
    if "__path__" in value:
        return Path(value["__path__"])
    if "__tuple__" in value:
        return tuple(decode_model(item) for item in value["__tuple__"])
    if "__type__" in value:
        cls = model_class(value["__type__"])
        accepted = {field.name for field in fields(cls) if field.init} if is_dataclass(cls) else None
        kwargs = {
            key: decode_model(item) for key, item in value.items()
            if key != "__type__" and (accepted is None or key in accepted)
        }
        return cls(**kwargs)
    return {key: decode_model(item) for key, item in value.items()}
