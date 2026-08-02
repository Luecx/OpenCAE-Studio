from dataclasses import dataclass, field

from ...core import register_model_type
from .region import Region


@register_model_type("element_set")
@dataclass
class ElementSet(Region):
    region_type: str = field(init=False, default="Element Set")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
