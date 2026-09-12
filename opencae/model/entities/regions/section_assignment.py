"""Assigns a Section object to one Part-local target region."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition

if TYPE_CHECKING:
    from ..sections import Section
    from .orientation import Orientation


@register_model_type("section_assignment")
@dataclass
class SectionAssignment(Entity):
    section: Section | None = field(
        default=None,
        metadata={"reference_type": "Section"},
    )
    target: RegionDefinition = field(default_factory=RegionDefinition)
    orientation: Orientation | None = field(
        default=None,
        metadata={"reference_type": "Orientation"},
    )

    def __post_init__(self):
        self.target = as_region_definition(self.target)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
