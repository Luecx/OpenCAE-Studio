"""Defines an executable analysis as an ordered reference list of shared steps."""

from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from .step import AnalysisStep


@register_model_type("analysis")
@dataclass
class Analysis(Entity):
    """Reusable analysis configuration referencing project-owned Steps."""

    analysis_type: str = "General"
    step_refs: list[EntityRef] = field(default_factory=list)
    solver: str = "FEMaster"
    deck_profile_id: str = "builtin:femaster"
    settings: dict[str, str] = field(default_factory=dict)

    def resolved_steps(self, project) -> tuple[AnalysisStep, ...]:
        """Resolve the configured Step order against the current Project graph."""
        return tuple(
            value
            for value in (project.try_resolve(ref) for ref in self.step_refs)
            if isinstance(value, AnalysisStep)
        )

    def bind_steps(self, steps) -> None:
        """Replace the analysis Step order with references to shared Steps."""
        items = tuple(steps)
        self.step_refs = [EntityRef.of(step, "AnalysisStep") for step in items]
        if items and self.analysis_type == "General":
            kinds = {step.step_type for step in items}
            if len(kinds) == 1:
                self.analysis_type = next(iter(kinds))

    def write_abaqus(self, writer, context) -> None:
        """Write all referenced Steps using the Abaqus exporter."""
        for step in self.resolved_steps(context.project):
            step.write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        """Write all referenced Steps using the FEMaster exporter."""
        for step in self.resolved_steps(context.project):
            step.write_femaster(writer, context)
