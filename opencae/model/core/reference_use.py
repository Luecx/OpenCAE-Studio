"""Defines one reverse-reference occurrence recorded by ProjectIndex."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReferenceUse:
    """Describes where one EntityRef targets another project entity."""

    source_id: str
    source_name: str
    field_path: str
    expected_type: str = ""
