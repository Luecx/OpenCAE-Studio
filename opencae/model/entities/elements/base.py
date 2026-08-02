from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("element_definition")
@dataclass
class ElementDefinition(Entity):
    category: str = "Solid Elements"
    topology: str = "Hexahedra"
    order: str = "Linear"
    formulation: str = "Standard"
    gmsh_type: int = 0
    count: int = 0

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
