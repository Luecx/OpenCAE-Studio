from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition


@register_model_type("support")
@dataclass
class Support(Entity):
    support_type: str = "Support"
    target: RegionDefinition = field(default_factory=RegionDefinition)
    coordinate_system_ref: EntityRef | None = None
    components: list[float | None] = field(default_factory=lambda: [None] * 6)

    def __post_init__(self): self.target = as_region_definition(self.target)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        return None
