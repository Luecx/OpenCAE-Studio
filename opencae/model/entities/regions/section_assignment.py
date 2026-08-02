from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type


@register_model_type("section_assignment")
@dataclass
class SectionAssignment(Entity):
    section_ref: EntityRef = field(default_factory=lambda: EntityRef(expected_type="Section"))
    region_ref: EntityRef = field(default_factory=lambda: EntityRef(expected_type="ElementSet"))
    orientation_ref: EntityRef | None = None

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
