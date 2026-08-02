from dataclasses import dataclass, field

from ...core import Entity, register_model_type


@register_model_type("mesh_control")
@dataclass
class MeshControl(Entity):
    scope: str = "Cell"
    topology: str = "Tetrahedral"
    technique: str = "Free"
    targets: list[str] = field(default_factory=list)

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
