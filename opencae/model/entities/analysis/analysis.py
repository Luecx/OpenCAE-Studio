from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from .step import AnalysisStep


@register_model_type("analysis")
@dataclass
class Analysis(Entity):
    analysis_type: str = "Linear Static"
    steps: list[AnalysisStep | str] = field(default_factory=list)
    solver: str = "FEMaster"
    settings: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        converted = []
        for index, step in enumerate(self.steps):
            if isinstance(step, AnalysisStep): converted.append(step)
            else: converted.append(AnalysisStep(name=str(step), step_type=self.analysis_type))
        self.steps = converted or [AnalysisStep(name="Step-1", step_type=self.analysis_type)]

    def write_abaqus(self, writer, context) -> None:
        for step in self.steps: step.write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        for step in self.steps: step.write_femaster(writer, context)
