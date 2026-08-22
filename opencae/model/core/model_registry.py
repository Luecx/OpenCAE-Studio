from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields, is_dataclass
from typing import TypeVar

T = TypeVar("T", bound=type)
MODEL_TYPES: dict[str, type] = {}


class _EntityObjectReference:
    """Public object view over a persisted ``*_ref`` field.

    Persistence keeps stable entity IDs in ``EntityRef`` objects. Application and
    public API code can use normal Python object references such as
    ``instance.part`` or ``section.material`` instead.
    """

    def __init__(self, ref_name: str, expected_type: str):
        self.ref_name = ref_name
        self.expected_type = expected_type
        self.cache_name = f"_resolved_{ref_name}"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        ref = getattr(instance, self.ref_name, None)
        if ref is None or not getattr(ref, "is_bound", False):
            instance.__dict__.pop(self.cache_name, None)
            return None

        cached = instance.__dict__.get(self.cache_name)
        if cached is not None and getattr(cached, "id", None) == ref.entity_id:
            return cached

        project = getattr(instance, "project", None)
        if project is None:
            return None
        resolved = project.try_resolve(ref)
        if resolved is not None:
            instance.__dict__[self.cache_name] = resolved
        return resolved

    def __set__(self, instance, value):
        from .entity import Entity
        from .reference import EntityRef

        if value is None:
            setattr(instance, self.ref_name, None)
            instance.__dict__.pop(self.cache_name, None)
            return
        if not isinstance(value, Entity):
            public_name = self.ref_name.removesuffix("_ref")
            raise TypeError(
                f"{type(instance).__name__}.{public_name} expects an Entity "
                f"object, not {type(value).__name__}"
            )

        current = getattr(instance, self.ref_name, None)
        expected = getattr(current, "expected_type", "") or self.expected_type
        setattr(instance, self.ref_name, EntityRef.of(value, expected))
        instance.__dict__[self.cache_name] = value


def _expected_type_from_field(name: str) -> str:
    return "".join(part.capitalize() for part in name.removesuffix("_ref").split("_"))


def _install_object_reference_aliases(cls: type) -> None:
    # Value objects such as selection operands also contain EntityRef fields, but
    # public object aliases belong on model entities only. Avoid touching frozen
    # / slotted persistence value objects.
    if not is_dataclass(cls) or not any(base.__name__ == "Entity" for base in cls.__mro__[1:]):
        return

    for info in fields(cls):
        if not info.name.endswith("_ref"):
            continue
        public_name = info.name[:-4]
        if hasattr(cls, public_name):
            continue
        setattr(
            cls,
            public_name,
            _EntityObjectReference(info.name, _expected_type_from_field(info.name)),
        )


def register_model_type(type_name: str) -> Callable[[T], T]:
    def decorate(cls: T) -> T:
        cls.model_type = type_name
        MODEL_TYPES[type_name] = cls
        _install_object_reference_aliases(cls)
        return cls
    return decorate


def model_class(type_name: str) -> type:
    try:
        return MODEL_TYPES[type_name]
    except KeyError as exc:
        raise ValueError(f"Unknown model type: {type_name}") from exc
