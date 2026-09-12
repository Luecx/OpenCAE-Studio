"""Classify persistent dataclass fields as owned state or object references."""

from __future__ import annotations

from dataclasses import Field


def is_persistent_model_field(field_info: Field) -> bool:
    """Return whether a field participates in persistent model serialization."""
    return (
        field_info.init
        and not field_info.name.startswith("_")
        and field_info.metadata.get("serialize", True)
    )


def reference_type_for_field(field_info: Field) -> str:
    """Return the declared type contract for a direct entity relationship."""
    return str(field_info.metadata.get("reference_type", "")).strip()


def is_reference_model_field(field_info: Field) -> bool:
    """Return whether a persistent field is a non-owning Entity relationship.

    Runtime domain objects store the referenced Entity object directly.  The
    persistence codec alone translates this field to/from a stable EntityRef.
    """
    return bool(
        is_persistent_model_field(field_info)
        and reference_type_for_field(field_info)
    )


def mesh_reference_kind(field_info: Field) -> str:
    """Return ``node``/``element`` for compact mesh-object relationships."""
    return str(field_info.metadata.get("mesh_reference", "")).strip().casefold()


def is_mesh_reference_field(field_info: Field) -> bool:
    """Return whether a field stores a canonical Node/Element object relationship."""
    return bool(is_persistent_model_field(field_info) and mesh_reference_kind(field_info))


def is_owned_model_field(field_info: Field) -> bool:
    """Return whether ProjectIndex should traverse the field for owned Entities."""
    return (
        is_project_index_field(field_info)
        and not is_reference_model_field(field_info)
        and not is_mesh_reference_field(field_info)
    )


def is_project_index_field(field_info: Field) -> bool:
    """Return whether a persistent field can affect identity/reference topology.

    Large numeric payloads such as node coordinates and element connectivity are
    persisted, but explicitly opt out with ``project_index=False``.  Direct
    relationship fields still participate in reference indexing while being
    excluded from ownership traversal by :func:`is_owned_model_field`.
    """
    return is_persistent_model_field(field_info) and field_info.metadata.get(
        "project_index",
        True,
    )
