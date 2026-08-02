from dataclasses import dataclass, field

from ...core import Entity, register_model_type


@register_model_type("analysis_step")
@dataclass
class AnalysisStep(Entity):
    step_type: str = "Linear Static"
    active_loads: list[str] = field(default_factory=list)
    active_supports: list[str] = field(default_factory=list)
    number_of_modes: int = 10
    time_period: float = 1.0
    settings: dict[str, object] = field(default_factory=dict)

    @property
    def uses_loads(self) -> bool:
        return self.step_type not in {"Eigenfrequency"}

    @property
    def uses_supports(self) -> bool:
        return True

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        from opencae.solvers.femaster_dsl.emitters.loadcase import write_step
        write_step(self, writer, context)
