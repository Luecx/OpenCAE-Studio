from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Support


@register_model_type("symmetry_support")
@dataclass
class SymmetrySupport(Support):
    support_type: str = field(init=False, default="Symmetry")
    components: list[float | None] = field(default_factory=lambda: [0.0, None, None, None, None, None])

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        super().write_femaster(writer, context)
