from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Load


@register_model_type("pressure_load")
@dataclass
class PressureLoad(Load):
    load_type: str = field(init=False, default="Pressure")
    pressure: float = 1.0
