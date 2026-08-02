from dataclasses import dataclass, field

from ...core import EntityRef, register_model_type
from .base import Load


@register_model_type("temperature_load")
@dataclass
class TemperatureLoad(Load):
    load_type: str = field(init=False, default="Temperature")
    temperature_field_ref: EntityRef | None = None
    reference_temperature: float = 0.0
