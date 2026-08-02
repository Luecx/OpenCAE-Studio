from dataclasses import dataclass, field

from ...core import Entity, register_model_type


@register_model_type("support")
@dataclass
class Support(Entity):
    support_type: str = "Support"
    region_name: str = ""
    coordinate_system: str = "Global"
    step_name: str = "Initial"
    components: list[float | None] = field(default_factory=lambda: [None] * 6)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.loads import write_support
        write_support(self, writer, context)
