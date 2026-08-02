from dataclasses import dataclass

from ...core import Entity, EntityRef, TargetRef, register_model_type


@register_model_type("load")
@dataclass
class Load(Entity):
    load_type: str = "Load"
    target: TargetRef | None = None
    coordinate_system_ref: EntityRef | None = None

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.loads import write_load
        write_load(self, writer, context)
