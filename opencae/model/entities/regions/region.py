from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition, RegionProjection, RegionScope


@register_model_type("region")
@dataclass
class Region(Entity):
    scope: RegionScope | str = RegionScope.PART
    definition: RegionDefinition = field(default_factory=RegionDefinition)
    preferred_projection: RegionProjection | str = RegionProjection.NODES
    geometry_backed: bool = True

    def __post_init__(self):
        self.scope = RegionScope(self.scope)
        projection = RegionProjection.coerce(self.preferred_projection)
        allowed = {
            RegionProjection.NODES,
            RegionProjection.ELEMENTS,
            RegionProjection.FACETS,
        }
        if projection not in allowed:
            raise ValueError("A region must be a node, element, or surface region")
        self.preferred_projection = projection
        self.definition = RegionDefinition.from_values(self.definition)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
