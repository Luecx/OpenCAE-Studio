from dataclasses import dataclass, field
from enum import StrEnum

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition


class ElementOrder(StrEnum):
    FIRST = "First"
    SECOND = "Second"


class ElementTopology(StrEnum):
    LINE = "line"
    SHELL_TRI = "shell_tri"
    SHELL_QUAD = "shell_quad"
    SOLID_TET = "solid_tet"
    SOLID_PYRAMID = "solid_pyramid"
    SOLID_WEDGE = "solid_wedge"
    SOLID_HEX = "solid_hex"


@register_model_type("element_control")
@dataclass
class ElementControl(Entity):
    target: RegionDefinition = field(default_factory=RegionDefinition)
    topology: ElementTopology | str = ElementTopology.SOLID_TET
    order: ElementOrder | str = ElementOrder.FIRST
    formulation: str = "Standard"

    def __post_init__(self):
        self.target = as_region_definition(self.target)
        self.topology = ElementTopology(self.topology)
        self.order = ElementOrder(self.order)

    @property
    def entire_part(self) -> bool: return self.target.empty

    def write_abaqus(self, writer, context) -> None: return None
    def write_femaster(self, writer, context) -> None: return None
