from dataclasses import dataclass, field

from ...core import register_model_type
from .analysis import Analysis


@register_model_type("buckling_analysis")
@dataclass
class BucklingAnalysis(Analysis):
    analysis_type: str = field(init=False, default="Linear Buckling")

    def write_abaqus(self, writer, context) -> None:
        super().write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        super().write_femaster(writer, context)
