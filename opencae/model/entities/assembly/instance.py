"""Defines one Assembly occurrence of a Part."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...core import Entity, register_model_type

if TYPE_CHECKING:
    from ..parts import Part


@register_model_type("instance")
@dataclass
class Instance(Entity):
    """One positioned Part occurrence using the Part object as its relationship."""

    part: Part | None = field(
        default=None,
        metadata={"reference_type": "Part"},
    )
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    suppressed: bool = False

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
