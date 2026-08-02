from dataclasses import dataclass, field

from ...core import Entity, RegionMemberRef, register_model_type


@register_model_type("region")
@dataclass
class Region(Entity):
    region_type: str = "Region"
    scope: str = "Part"
    members: list[RegionMemberRef | str] = field(default_factory=list)
    geometry_backed: bool = True

    def write_abaqus(self, writer, context) -> None:
        return None

    def write_femaster(self, writer, context) -> None:
        return None
