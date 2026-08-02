from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Load


@register_model_type("body_load")
@dataclass
class BodyLoad(Load):
    load_type: str = field(init=False, default="Body load")
    magnitude: float = 0.0
    direction: str = "Global Z"
