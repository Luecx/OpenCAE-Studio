from dataclasses import dataclass, field

from ...core import register_model_type
from .control import MeshControl


@register_model_type("free_mesh_control")
@dataclass
class FreeMeshControl(MeshControl):
    technique: str = field(init=False, default="Free")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
