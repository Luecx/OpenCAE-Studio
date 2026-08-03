from dataclasses import dataclass, field
from typing import Any

from ...core import Entity, register_model_type
from .calculations import profile_properties


@register_model_type("profile")
@dataclass
class Profile(Entity):
    profile_type: str = "General"
    dimensions: dict[str, Any] = field(default_factory=dict)

    def properties(self) -> dict[str, float]:
        return profile_properties(self.profile_type, self.dimensions)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        return None
