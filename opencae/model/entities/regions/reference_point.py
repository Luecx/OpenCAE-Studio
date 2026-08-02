from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("reference_point")
@dataclass
class ReferencePoint(Entity):
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scope: str = "Part"

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
