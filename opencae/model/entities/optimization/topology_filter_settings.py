"""Stores topology filtering settings and the two independent filter radii."""

from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from .filter_radius import FilterRadius


@register_model_type("topology_filter_settings")
@dataclass
class TopologyFilterSettings(Entity):
    """Configuration for density coupling and sensitivity regularization."""

    name: str = "Topology Filter"
    enabled: bool = True
    density_constraint_radius: FilterRadius = field(
        default_factory=lambda: FilterRadius(True, 2.5, 0.0)
    )
    sensitivity_radius: FilterRadius = field(
        default_factory=lambda: FilterRadius(True, 5.0, 0.0)
    )
    density_weighted_sensitivities: bool = True
