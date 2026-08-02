from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("orientation")
@dataclass
class Orientation(Entity):
    region_name: str = ""
    coordinate_system_name: str = "Global"
    orientation_type: str = "Material"

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
