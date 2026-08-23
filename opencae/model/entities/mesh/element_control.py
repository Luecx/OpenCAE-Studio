"""Defines one persistent mesh element-control assignment."""

from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition
from .element_order import ElementOrder
from .element_topology import ElementTopology


@register_model_type("element_control")
@dataclass
class ElementControl(Entity):
    """Assigns topology, order, and formulation to a region of one Part mesh."""

    target: RegionDefinition = field(default_factory=RegionDefinition)
    topology: ElementTopology | str = ElementTopology.SOLID_TET
    order: ElementOrder | str = ElementOrder.FIRST
    formulation: str = "Standard"

    def __post_init__(self) -> None:
        """Normalize selection and finite-domain topology/order values."""
        self.target = as_region_definition(self.target)
        self.topology = ElementTopology(self.topology)
        self.order = ElementOrder(self.order)

    @property
    def entire_part(self) -> bool:
        """Return whether this control applies to the whole owning Part."""
        return self.target.empty

    def write_abaqus(self, writer, context) -> None:
        """Element-control export is handled by the meshing/export pipeline."""
        return None

    def write_femaster(self, writer, context) -> None:
        """Element-control export is handled by the meshing/export pipeline."""
        return None
