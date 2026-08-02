from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Support


@register_model_type("displacement_support")
@dataclass
class DisplacementSupport(Support):
    support_type: str = field(init=False, default="Displacement")
    components: list[float | None] = field(default_factory=lambda: [None] * 6)

    def write_abaqus(self, writer, context) -> None:
        return None
