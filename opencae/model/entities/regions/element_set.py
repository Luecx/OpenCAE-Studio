from dataclasses import dataclass, field

from ...core import register_model_type
from opencae.model.selection import RegionProjection
from .region import Region


@register_model_type("element_set")
@dataclass
class ElementSet(Region):
    preferred_projection: RegionProjection = field(init=False, default=RegionProjection.ELEMENTS)
