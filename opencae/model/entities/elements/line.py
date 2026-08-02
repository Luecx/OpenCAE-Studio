from dataclasses import dataclass, field

from ...core import register_model_type
from .base import ElementDefinition


@register_model_type("line_element_definition")
@dataclass
class LineElementDefinition(ElementDefinition):
    category: str = field(init=False, default="Line Elements")
    topology: str = field(init=False, default="Lines")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
