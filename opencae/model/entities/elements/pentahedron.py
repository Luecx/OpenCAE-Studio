from dataclasses import dataclass, field

from ...core import register_model_type
from .base import ElementDefinition


@register_model_type("pentahedron_element_definition")
@dataclass
class PentahedronElementDefinition(ElementDefinition):
    category: str = field(init=False, default="Solid Elements")
    topology: str = field(init=False, default="Pentahedra")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
