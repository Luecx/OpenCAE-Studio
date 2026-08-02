from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type


@register_model_type("instance")
@dataclass
class Instance(Entity):
    part_ref: EntityRef = field(default_factory=lambda: EntityRef(expected_type="Part"))
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    suppressed: bool = False

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
