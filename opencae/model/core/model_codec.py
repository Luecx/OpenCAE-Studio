"""Encode/decode registered model dataclasses and object relationships."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .model_registry import model_class
from .persistent_model_field import (
    is_mesh_reference_field,
    is_persistent_model_field,
    is_reference_model_field,
    reference_type_for_field,
)
from .reference import EntityRef


def encode_model(value: Any) -> Any:
    """Convert one model value into JSON-compatible registered type data.

    Domain relationships are normal Python objects.  Only at this persistence
    boundary are reference fields reduced to stable ``EntityRef`` records and
    compact mesh-object references reduced to their integer mesh IDs.
    """
    if is_dataclass(value):
        type_name = getattr(type(value), "model_type", None)
        data = {}
        for field_info in fields(value):
            if not is_persistent_model_field(field_info):
                continue
            item = getattr(value, field_info.name)
            if is_reference_model_field(field_info):
                data[field_info.name] = _encode_entity_reference(
                    item,
                    reference_type_for_field(field_info),
                )
            elif is_mesh_reference_field(field_info):
                data[field_info.name] = _encode_mesh_reference(item)
            else:
                data[field_info.name] = encode_model(item)
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


def _encode_entity_reference(value: Any, expected_type: str) -> Any:
    """Encode direct Entity relationships without recursively owning targets."""
    if value is None:
        return None
    if isinstance(value, list):
        return [
            _encode_entity_reference(item, expected_type)
            for item in value
        ]
    if isinstance(value, tuple):
        return {
            "__tuple__": [
                _encode_entity_reference(item, expected_type)
                for item in value
            ]
        }
    if isinstance(value, dict):
        return {
            key: _encode_entity_reference(item, expected_type)
            for key, item in value.items()
        }
    return encode_model(EntityRef.of(value, expected_type))


def _encode_mesh_reference(value: Any) -> Any:
    """Encode canonical Node/Element relationships as compact local IDs."""
    if value is None:
        return None
    if isinstance(value, list):
        return [_encode_mesh_reference(item) for item in value]
    if isinstance(value, tuple):
        return {"__tuple__": [_encode_mesh_reference(item) for item in value]}
    if isinstance(value, dict):
        return {key: _encode_mesh_reference(item) for key, item in value.items()}
    if isinstance(value, int):
        return int(value)
    identity = getattr(value, "id", None)
    if identity is None:
        raise TypeError(
            f"Mesh reference expects a Node/Element object, got {type(value).__name__}"
        )
    return int(identity)


def decode_model(value: Any) -> Any:
    """Reconstruct model data, leaving references for Project binding.

    Reference fields initially contain decoded ``EntityRef`` objects (and mesh
    reference fields contain integer IDs).  ``Project.rebuild_index`` resolves
    those wire values to the canonical runtime objects before exposing the graph.
    """
    if isinstance(value, list):
        return [decode_model(item) for item in value]
    if not isinstance(value, dict):
        return value

    if "__path__" in value:
        unknown = set(value) - {"__path__"}
        if unknown:
            raise ValueError(
                f"Unexpected path fields: {', '.join(sorted(unknown))}"
            )
        return Path(value["__path__"])

    if "__tuple__" in value:
        unknown = set(value) - {"__tuple__"}
        if unknown:
            raise ValueError(
                f"Unexpected tuple fields: {', '.join(sorted(unknown))}"
            )
        return tuple(decode_model(item) for item in value["__tuple__"])

    if "__type__" in value:
        type_name = value["__type__"]
        cls = model_class(type_name)
        if is_dataclass(cls):
            accepted = {
                field_info.name
                for field_info in fields(cls)
                if is_persistent_model_field(field_info)
            }
            unknown = set(value) - accepted - {"__type__"}
            if unknown:
                names = ", ".join(sorted(unknown))
                raise ValueError(
                    f"Unknown persisted field(s) for {type_name}: {names}"
                )
        else:
            accepted = None

        kwargs = {
            key: decode_model(item)
            for key, item in value.items()
            if key != "__type__" and (accepted is None or key in accepted)
        }
        return cls(**kwargs)

    return {key: decode_model(item) for key, item in value.items()}
