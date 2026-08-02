from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Support


@register_model_type("temperature_support")
@dataclass
class TemperatureSupport(Support):
    support_type: str = field(init=False, default="Temperature")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        super().write_femaster(writer, context)
