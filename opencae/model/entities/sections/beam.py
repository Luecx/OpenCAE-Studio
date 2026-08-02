from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Section


@register_model_type("beam_section")
@dataclass
class BeamSection(Section):
    section_type: str = field(init=False, default="Beam")
    profile_name: str = ""
    direction: tuple[float, float, float] = (0.0, 1.0, 0.0)
