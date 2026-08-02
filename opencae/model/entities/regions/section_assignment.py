from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("section_assignment")
@dataclass
class SectionAssignment(Entity):
    section_name: str = ""
    region_name: str = ""
    orientation_name: str = "Global"

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
