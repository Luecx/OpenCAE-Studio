from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition


@register_model_type("section_assignment")
@dataclass
class SectionAssignment(Entity):
    section_ref: EntityRef = field(default_factory=lambda: EntityRef(expected_type="Section"))
    target: RegionDefinition = field(default_factory=RegionDefinition)
    orientation_ref: EntityRef | None = None

    def __post_init__(self): self.target = as_region_definition(self.target)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
