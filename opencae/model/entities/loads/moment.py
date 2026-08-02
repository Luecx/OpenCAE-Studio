from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Load


@register_model_type("moment_load")
@dataclass
class MomentLoad(Load):
    load_type: str = field(init=False, default="Moment")
    magnitude: float = 0.0
    direction: str = "Global X"
