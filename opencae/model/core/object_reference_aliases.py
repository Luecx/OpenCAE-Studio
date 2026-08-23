"""Installs object-facing aliases for persisted ``*_ref`` entity fields."""

from __future__ import annotations

from dataclasses import fields, is_dataclass

from .object_reference import EntityObjectReference


def install_object_reference_aliases(cls: type) -> None:
    """Attach object descriptors to Entity dataclasses that store EntityRef fields."""
    # Selection operands also contain EntityRef fields, but they are immutable
    # value objects rather than entities with a Project binding.
    if not is_dataclass(cls) or not any(
        base.__name__ == "Entity" for base in cls.__mro__[1:]
    ):
        return

    for field_info in fields(cls):
        if not field_info.name.endswith("_ref"):
            continue
        public_name = field_info.name[:-4]
        if hasattr(cls, public_name):
            continue
        setattr(
            cls,
            public_name,
            EntityObjectReference(
                field_info.name,
                expected_type_from_field(field_info.name),
            ),
        )


def expected_type_from_field(name: str) -> str:
    """Derive a default model type name from a snake-case ``*_ref`` field."""
    return "".join(
        part.capitalize()
        for part in name.removesuffix("_ref").split("_")
    )
