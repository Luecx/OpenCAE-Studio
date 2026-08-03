from dataclasses import dataclass

from ...core import Entity, EntityRef, register_model_type


@register_model_type("section")
@dataclass
class Section(Entity):
    section_type: str = "Section"
    material_ref: EntityRef | None = None
    profile_ref: EntityRef | None = None
    thickness: float = 0.0

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        return None
