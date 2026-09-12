"""Defines an executable analysis as an ordered list of shared Step objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from .step import AnalysisStep


@register_model_type("analysis")
@dataclass
class Analysis(Entity):
    """Reusable analysis configuration referencing project-owned Steps directly."""

    analysis_type: str = "General"
    steps: list[AnalysisStep] = field(
        default_factory=list,
        metadata={"reference_type": "AnalysisStep"},
    )
    solver: str = "FEMaster"
    deck_profile_id: str = "builtin:femaster"
    settings: dict[str, str] = field(default_factory=dict)

    def resolved_steps(self, project=None) -> tuple[AnalysisStep, ...]:
        """Return the configured Step order without ID resolution."""
        return tuple(self.steps)

    def bind_steps(self, steps) -> None:
        """Replace the analysis Step order with canonical Step objects."""
        items = tuple(steps)
        if not all(isinstance(step, AnalysisStep) for step in items):
            raise TypeError("Analysis.steps accepts AnalysisStep objects only")
        self.steps = list(items)
        if items and self.analysis_type == "General":
            kinds = {step.step_type for step in items}
            if len(kinds) == 1:
                self.analysis_type = next(iter(kinds)).value

    def write_abaqus(self, writer, context) -> None:
        for step in self.steps:
            step.write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        for step in self.steps:
            step.write_femaster(writer, context)
