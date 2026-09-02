"""Classifies dataclass fields used by persistence and runtime graph indexing."""

from dataclasses import Field


def is_persistent_model_field(field_info: Field) -> bool:
    """Return whether a field participates in persistent model serialization."""
    return (
        field_info.init
        and not field_info.name.startswith("_")
        and field_info.metadata.get("serialize", True)
    )


def is_project_index_field(field_info: Field) -> bool:
    """Return whether a persistent field can contain model identity or references.

    Large numeric payloads such as node coordinates and element connectivity are
    persisted, but they cannot own :class:`Entity` objects or contain
    :class:`EntityRef` relationships.  Such fields opt out with
    ``metadata={"project_index": False}`` so ProjectIndex and reference
    validation do not repeatedly walk millions of scalar values.
    """
    return is_persistent_model_field(field_info) and field_info.metadata.get(
        "project_index",
        True,
    )
