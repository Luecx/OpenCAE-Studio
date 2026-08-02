from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Section


@register_model_type("cohesive_section")
@dataclass
class CohesiveSection(Section):
    section_type: str = field(init=False, default="Cohesive")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
