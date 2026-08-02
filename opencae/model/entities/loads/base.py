from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("load")
@dataclass
class Load(Entity):
    load_type: str = "Load"
    region_name: str = ""
    step_name: str = "Step-1"

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.loads import write_load
        write_load(self, writer, context)
