from dataclasses import dataclass, field
from ...core import register_model_type
from .base import Profile

@register_model_type("u_profile")
@dataclass
class UProfile(Profile):
    profile_type: str = field(init=False, default="U-profile")
    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: super().write_femaster(writer, context)
