from .control import MeshControl
from .free_control import FreeMeshControl
from .structured_control import StructuredMeshControl
from .sweep_control import SweepMeshControl

_TYPES = {
    "Free": FreeMeshControl,
    "Sweep": SweepMeshControl,
    "Structured": StructuredMeshControl,
    "Transfinite": StructuredMeshControl,
}


def create_mesh_control(technique: str, **kwargs) -> MeshControl:
    cls = _TYPES.get(technique, MeshControl)
    if cls is MeshControl:
        return cls(technique=technique, **kwargs)
    return cls(**kwargs)
