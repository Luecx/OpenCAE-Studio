from dataclasses import dataclass, field

from ...core import register_model_type
from .base import ElementDefinition


@register_model_type("quadrilateral_shell_element_definition")
@dataclass
class QuadrilateralShellElementDefinition(ElementDefinition):
    category: str = field(init=False, default="Shell Elements")
    topology: str = field(init=False, default="Quadrilaterals")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
