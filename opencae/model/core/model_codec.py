"""Encodes and decodes registered persistent model dataclasses."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .model_registry import model_class
from .persistent_model_field import is_persistent_model_field

_MODEL_REF_KEY = "__model_ref__"


def encode_model(value: Any) -> Any:
    """Convert one model value into JSON-compatible registered type data.

    Most OpenCAE relationships use explicit ``EntityRef`` value objects.  A few
    tightly-owned model graphs (currently the parametric Sketcher) intentionally
    expose direct Python object relationships instead.  Classes participating in
    such a graph opt in with ``__model_identity__ = True``.  The first occurrence
    is encoded normally; subsequent occurrences become a small identity reference.
    IDs therefore remain a serialization detail while the in-memory model keeps
    real object relationships.
    """

    return _encode_model(value, {})


def _encode_model(value: Any, identities: dict[str, Any]) -> Any:
    if is_dataclass(value):
        identity = _identity_of(value)
        if identity:
            existing = identities.get(identity)
            if existing is value:
                return {_MODEL_REF_KEY: identity}
            if existing is not None:
                raise ValueError(
                    f"Duplicate persistent model identity '{identity}' for "
                    f"{type(value).__name__}"
                )
            identities[identity] = value

        type_name = getattr(type(value), "model_type", None)
        data = {
            field_info.name: _encode_model(
                getattr(value, field_info.name), identities
            )
            for field_info in fields(value)
            if is_persistent_model_field(field_info)
        }
        return {"__type__": type_name, **data} if type_name else data
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return {"__path__": str(value)}
    if isinstance(value, tuple):
        return {
            "__tuple__": [_encode_model(item, identities) for item in value]
        }
    if isinstance(value, list):
        return [_encode_model(item, identities) for item in value]
    if isinstance(value, dict):
        return {
            key: _encode_model(item, identities)
            for key, item in value.items()
        }
    return value


def decode_model(value: Any) -> Any:
    """Reconstruct one model value and reject fields outside the current schema."""

    return _decode_model(value, {})


def _decode_model(value: Any, identities: dict[str, Any]) -> Any:
    if isinstance(value, list):
        return [_decode_model(item, identities) for item in value]
    if not isinstance(value, dict):
        return value

    if _MODEL_REF_KEY in value:
        unknown = set(value) - {_MODEL_REF_KEY}
        if unknown:
            raise ValueError(
                "Unexpected model-reference fields: "
                + ", ".join(sorted(unknown))
            )
        identity = str(value[_MODEL_REF_KEY] or "")
        try:
            return identities[identity]
        except KeyError as exc:
            raise ValueError(
                f"Model reference '{identity}' appears before its owned object"
            ) from exc

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
        return tuple(
            _decode_model(item, identities) for item in value["__tuple__"]
        )

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
            key: _decode_model(item, identities)
            for key, item in value.items()
            if key != "__type__" and (accepted is None or key in accepted)
        }
        result = cls(**kwargs)
        identity = _identity_of(result)
        if identity:
            existing = identities.get(identity)
            if existing is not None and existing is not result:
                raise ValueError(
                    f"Duplicate decoded model identity '{identity}'"
                )
            identities[identity] = result
        return result

    return {
        key: _decode_model(item, identities)
        for key, item in value.items()
    }


def _identity_of(value: Any) -> str:
    """Return the explicit graph identity for opt-in model objects."""

    if not bool(getattr(type(value), "__model_identity__", False)):
        return ""
    return str(getattr(value, "id", "") or "")
