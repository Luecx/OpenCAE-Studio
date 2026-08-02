from dataclasses import dataclass, field
from ...core import register_model_type
from .base import Section

@register_model_type("solid_section")
@dataclass
class SolidSection(Section):
    section_type: str = field(init=False, default="Solid")
