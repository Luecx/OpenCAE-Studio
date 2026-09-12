"""Defines reusable Section entities with direct resource relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type

if TYPE_CHECKING:
    from ..profiles import Profile
    from ..resources import Material


@register_model_type("section")
@dataclass
class Section(Entity):
    """Base section referencing Material/Profile objects directly."""

    section_type: str = "Section"
    material: Material | None = field(
        default=None,
        metadata={"reference_type": "Material"},
    )
    profile: Profile | None = field(
        default=None,
        metadata={"reference_type": "Profile"},
    )
    thickness: float = 0.0

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
