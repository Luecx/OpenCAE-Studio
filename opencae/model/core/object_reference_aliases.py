"""Installs object-facing aliases for explicitly typed ``*_ref`` fields."""

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
                reference_type_for_field(field_info),
            ),
        )


def reference_type_for_field(field_info) -> str:
    """Return the declared object type for one persisted reference field.

    Field names are display-oriented implementation details and cannot express
    aliases such as ``temperature_field_ref -> FieldDefinition`` or union
    relationships such as ``source_ref -> Entity``. Requiring metadata keeps
    one authoritative contract for generated object-facing properties.
    """
    expected_type = str(field_info.metadata.get("reference_type", "")).strip()
    if not expected_type:
        raise TypeError(
            f"{field_info.name} must declare metadata "
            "{'reference_type': '<ModelType>'}"
        )
    return expected_type
