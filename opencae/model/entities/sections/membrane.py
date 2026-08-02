from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Section


@register_model_type("membrane_section")
@dataclass
class MembraneSection(Section):
    section_type: str = field(init=False, default="Membrane")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
