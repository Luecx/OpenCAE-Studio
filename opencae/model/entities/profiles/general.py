from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Profile


@register_model_type("general_profile")
@dataclass
class GeneralProfile(Profile):
    profile_type: str = field(init=False, default="General")

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        super().write_femaster(writer, context)
