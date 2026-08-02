from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Support


@register_model_type("fixed_support")
@dataclass
class FixedSupport(Support):
    support_type: str = field(init=False, default="Fixed")
    components: list[float | None] = field(default_factory=lambda: [0.0] * 6)

    def write_abaqus(self, writer, context) -> None:
        return None
