from dataclasses import dataclass, field
from ...core import register_model_type
from .base import Section

@register_model_type("truss_section")
@dataclass
class TrussSection(Section):
    section_type: str = field(init=False, default="Truss")
    area: float = 1.0
