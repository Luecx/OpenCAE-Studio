"""Beam-section model with an explicit local n1 orientation axis."""

from dataclasses import dataclass, field

from ...core import register_model_type
from .base import Section


@register_model_type("beam_section")
@dataclass
class BeamSection(Section):
    """Assign a profile and its approximate first local section axis to beams."""

    section_type: str = field(init=False, default="Beam")
    n1: tuple[float, float, float] = (0.0, 1.0, 0.0)

    def __post_init__(self) -> None:
        """Keep the persisted n1 vector finite in shape and non-zero in length."""
        values = tuple(float(value) for value in self.n1)
        if len(values) != 3:
            raise ValueError("Beam section n1 must contain exactly three components")
        if sum(value * value for value in values) <= 1.0e-24:
            raise ValueError("Beam section n1 must be a non-zero vector")
        self.n1 = values
