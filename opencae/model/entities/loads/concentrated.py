from dataclasses import dataclass, field
from ...core import register_model_type
from .base import Load


@register_model_type("concentrated_load")
@dataclass
class ConcentratedLoad(Load):
    load_type: str = field(init=False, default="Concentrated Load")
    components: list[float] = field(default_factory=lambda: [0.0] * 6)
    coordinate_system: str = "Global"
