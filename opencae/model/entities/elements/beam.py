from dataclasses import dataclass, field

from ...core import register_model_type
from .base import ElementDefinition


@register_model_type("beam_element_definition")
@dataclass
class BeamElementDefinition(ElementDefinition):
    category: str = field(init=False, default="Line Elements")
    topology: str = field(init=False, default="Beam Elements")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
