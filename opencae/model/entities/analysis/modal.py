from dataclasses import dataclass, field

from ...core import register_model_type
from .analysis import Analysis


@register_model_type("modal_analysis")
@dataclass
class ModalAnalysis(Analysis):
    analysis_type: str = field(init=False, default="Eigenfrequency")

    def write_abaqus(self, writer, context) -> None:
        super().write_abaqus(writer, context)

    def write_femaster(self, writer, context) -> None:
        super().write_femaster(writer, context)
