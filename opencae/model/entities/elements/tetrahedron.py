from dataclasses import dataclass, field

from ...core import register_model_type
from .base import ElementDefinition


@register_model_type("tetrahedron_element_definition")
@dataclass
class TetrahedronElementDefinition(ElementDefinition):
    category: str = field(init=False, default="Solid Elements")
    topology: str = field(init=False, default="Tetrahedra")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
