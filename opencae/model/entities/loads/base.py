from dataclasses import dataclass, field

from ...core import Entity, EntityRef, register_model_type
from opencae.model.selection import RegionDefinition


@register_model_type("load")
@dataclass
class Load(Entity):
    load_type: str = "Load"
    target: RegionDefinition = field(default_factory=RegionDefinition)
    coordinate_system_ref: EntityRef | None = None
    amplitude_ref: EntityRef | None = None

    def __post_init__(self):
        from opencae.model.selection import as_region_definition
        self.target = as_region_definition(self.target)

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None:
        return None
