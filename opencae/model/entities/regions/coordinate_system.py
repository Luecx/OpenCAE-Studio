from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("coordinate_system")
@dataclass
class CoordinateSystem(Entity):
    system_type: str = "Cartesian"
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    axis_1: tuple[float, float, float] = (1.0, 0.0, 0.0)
    axis_2: tuple[float, float, float] = (0.0, 1.0, 0.0)
    scope: str = "Part"

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
