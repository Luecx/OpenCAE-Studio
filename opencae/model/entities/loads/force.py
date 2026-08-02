from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Load


@register_model_type("force_load")
@dataclass
class ForceLoad(Load):
    load_type: str = field(init=False, default="Force")
    magnitude: float = 0.0
    direction: str = "Global X"
    coordinate_system: str = "Global"
