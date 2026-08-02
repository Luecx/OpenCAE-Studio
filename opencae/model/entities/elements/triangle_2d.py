from dataclasses import dataclass, field

from ...core import register_model_type
from .base import ElementDefinition


@register_model_type("triangle_2d_element_definition")
@dataclass
class Triangle2DElementDefinition(ElementDefinition):
    category: str = field(init=False, default="2D Elements")
    topology: str = field(init=False, default="Triangles")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
