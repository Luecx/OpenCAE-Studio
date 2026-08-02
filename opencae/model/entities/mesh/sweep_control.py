from dataclasses import dataclass, field

from ...core import register_model_type
from .control import MeshControl


@register_model_type("sweep_mesh_control")
@dataclass
class SweepMeshControl(MeshControl):
    technique: str = field(init=False, default="Sweep")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
