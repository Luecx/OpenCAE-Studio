from dataclasses import dataclass, field
from ...core import register_model_type
from .base import Load


@register_model_type("volume_load")
@dataclass
class VolumeLoad(Load):
    load_type: str = field(init=False, default="Volume Load")
    components: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    coordinate_system: str = "Global"
