from dataclasses import dataclass, field

from ...core import register_model_type
from .analysis import Analysis


@register_model_type("transient_analysis")
@dataclass
class TransientAnalysis(Analysis):
    analysis_type: str = field(init=False, default="Transient")

    def write_abaqus(self, writer, context) -> None:
        super().write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        super().write_femaster(writer, context)
