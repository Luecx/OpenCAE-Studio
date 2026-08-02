from dataclasses import dataclass, field

from ...core import register_model_type
from .control import MeshControl


@register_model_type("structured_mesh_control")
@dataclass
class StructuredMeshControl(MeshControl):
    technique: str = field(init=False, default="Structured")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
