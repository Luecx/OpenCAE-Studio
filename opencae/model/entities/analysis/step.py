from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type


@register_model_type("analysis_step")
@dataclass
class AnalysisStep(Entity):
    step_type: str = "Linear Static"
    load_refs: list[EntityRef] = field(default_factory=list)
    support_refs: list[EntityRef] = field(default_factory=list)
    number_of_modes: int = 10
    time_period: float = 1.0
    settings: dict[str, object] = field(default_factory=dict)

    @property
    def uses_loads(self) -> bool: return self.step_type not in {"Eigenfrequency"}
    @property
    def uses_supports(self) -> bool: return True
    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        return None
