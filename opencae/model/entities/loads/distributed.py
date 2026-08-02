from dataclasses import dataclass, field
from ...core import register_model_type
from .base import Load


@register_model_type("distributed_load")
@dataclass
class DistributedLoad(Load):
    load_type: str = field(init=False, default="Surface Traction")
    components: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
