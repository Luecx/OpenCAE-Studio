"""Defines an executable analysis as an ordered reference list of shared steps."""

from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from .step import AnalysisStep


@register_model_type("analysis")
@dataclass
class Analysis(Entity):
    """Reusable analysis configuration referencing project-level steps."""

    analysis_type: str = "General"
    step_refs: list[EntityRef] = field(default_factory=list)
    solver: str = "FEMaster"
    settings: dict[str, str] = field(default_factory=dict)
    # Accepted only to migrate projects written before steps became top-level.
    steps: list[AnalysisStep | str] = field(
        default_factory=list,
        metadata={"serialize": False},
    )

    def __post_init__(self):
        converted = []
        for step in self.steps:
            if isinstance(step, AnalysisStep):
                converted.append(step)
            else:
                converted.append(
                    AnalysisStep(name=str(step), step_type=self.analysis_type)
                )
        self.steps = converted

    def resolved_steps(self, project) -> tuple[AnalysisStep, ...]:
        """Resolve the configured step order against the current project graph."""

        resolved = tuple(
            value
            for value in (project.try_resolve(ref) for ref in self.step_refs)
            if isinstance(value, AnalysisStep)
        )
        return resolved or tuple(self.steps)

    def bind_steps(self, steps) -> None:
        """Replace the analysis step order with references to shared steps."""

        self.step_refs = [EntityRef.of(step, "AnalysisStep") for step in steps]
        self.steps = []
        if steps and self.analysis_type == "General":
            kinds = {step.step_type for step in steps}
            if len(kinds) == 1:
                self.analysis_type = next(iter(kinds))

    def write_abaqus(self, writer, context) -> None:
        for step in self.resolved_steps(context.project):
            step.write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        for step in self.resolved_steps(context.project):
            step.write_femaster(writer, context)
