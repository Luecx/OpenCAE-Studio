"""Classifies dataclass fields that belong to the persistent model graph."""

from dataclasses import Field


def is_persistent_model_field(field_info: Field) -> bool:
    """Return whether a field participates in persistence and graph traversal."""
    return (
        field_info.init
        and not field_info.name.startswith("_")
        and field_info.metadata.get("serialize", True)
    )
