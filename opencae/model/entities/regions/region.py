from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition, RegionProjection, RegionScope


@register_model_type("region")
@dataclass
class Region(Entity):
    scope: RegionScope | str = RegionScope.PART
    definition: RegionDefinition = field(default_factory=RegionDefinition)
    preferred_projection: RegionProjection | str | None = None
    geometry_backed: bool = True

    def __post_init__(self):
        self.scope = RegionScope(self.scope)
        self.preferred_projection = RegionProjection.coerce(self.preferred_projection)
        self.definition = RegionDefinition.from_values(self.definition)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
