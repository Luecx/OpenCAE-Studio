from dataclasses import dataclass

from ...core import Entity, register_model_type


@register_model_type("instance")
@dataclass
class Instance(Entity):
    part_name: str = ""
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    suppressed: bool = False

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
