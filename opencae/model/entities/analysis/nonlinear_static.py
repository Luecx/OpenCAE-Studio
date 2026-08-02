from dataclasses import dataclass, field

from ...core import register_model_type
from .analysis import Analysis


@register_model_type("nonlinear_static_analysis")
@dataclass
class NonlinearStaticAnalysis(Analysis):
    analysis_type: str = field(init=False, default="Nonlinear Static")

    def write_abaqus(self, writer, context) -> None:
        super().write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        super().write_femaster(writer, context)
