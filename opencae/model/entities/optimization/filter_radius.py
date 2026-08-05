"""Stores one automatic or manual radius used by topology sparse operators."""

from dataclasses import dataclass

from ...core import register_model_type


@register_model_type("topology_filter_radius")
@dataclass
class FilterRadius:
    """Radius definition resolved once from the design-element spacing."""

    automatic: bool = True
    factor: float = 2.5
    value: float = 0.0

    def resolved(self, minimum_distance: float) -> float:
        """Return the effective positive radius for a mesh spacing."""

        minimum = max(float(minimum_distance), 1.0e-12)
        if self.automatic:
            return max(float(self.factor) * minimum, minimum)
        return max(float(self.value), 1.0e-12)
