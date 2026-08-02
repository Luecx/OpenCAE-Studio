from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type


@register_model_type("field_definition")
@dataclass
class FieldDefinition(Entity):
    location: str = "Nodal"
    components: int = 1
    component_names: list[str] = field(default_factory=lambda: ["Value"])
    region_ref: EntityRef | None = None
    source_type: str = "Formula"
    expression: str = "0.0"
    table: list[list[str]] = field(default_factory=list)
    file_path: str = ""
    interpolation: str = "Linear"
    field_type: str = "Scalar"

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.resources import write_field
        write_field(self, writer, context)
