"""Encodes and decodes registered persistent model dataclasses."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .model_registry import model_class
from .persistent_model_field import is_persistent_model_field


def encode_model(value: Any) -> Any:
    """Convert one model value into JSON-compatible registered type data."""
    if is_dataclass(value):
        type_name = getattr(type(value), "model_type", None)
        data = {
            field_info.name: encode_model(getattr(value, field_info.name))
            for field_info in fields(value)
            if is_persistent_model_field(field_info)
        }
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
    """Reconstruct one model value from registered JSON-compatible type data."""
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
        accepted = (
            {field_info.name for field_info in fields(cls) if field_info.init}
            if is_dataclass(cls)
            else None
        )
        kwargs = {
            key: decode_model(item)
            for key, item in value.items()
            if key != "__type__" and (accepted is None or key in accepted)
        }
        return cls(**kwargs)
    return {key: decode_model(item) for key, item in value.items()}
