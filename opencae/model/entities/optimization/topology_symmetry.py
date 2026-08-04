"""Defines one planar or rotational symmetry constraint for topology optimization."""

from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from .symmetry_type import SymmetryType


@register_model_type("topology_symmetry")
@dataclass
class TopologySymmetry(Entity):
    """A geometric symmetry reference and its rotational occurrence count."""

    symmetry_type: SymmetryType | str = SymmetryType.PLANAR
    reference: dict = field(default_factory=dict)
    occurrences: int = 2
    enabled: bool = True

    def __post_init__(self):
        self.symmetry_type = SymmetryType(self.symmetry_type)
        self.reference = dict(self.reference or {})
        self.occurrences = max(2, int(self.occurrences))
        if self.symmetry_type == SymmetryType.PLANAR:
            self.occurrences = 2
