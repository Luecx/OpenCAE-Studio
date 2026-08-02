from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("section")
@dataclass
class Section(Entity):
    section_type: str = "Section"
    material_name: str = ""
    profile_name: str = ""
    thickness: float = 0.0

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.resources import write_section
        elset = context.options.get("elset")
        if elset: write_section(self, elset, context.options.get("orientation"), writer, context)
        else: writer.comment(f"Section {self.name} requires a section assignment / ELSET")
