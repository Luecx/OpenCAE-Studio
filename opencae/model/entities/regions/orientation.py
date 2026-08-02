from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type


@register_model_type("orientation")
@dataclass
class Orientation(Entity):
    region_ref: EntityRef = field(default_factory=lambda: EntityRef(expected_type="ElementSet"))
    coordinate_system_ref: EntityRef | None = None
    orientation_type: str = "Material"

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
