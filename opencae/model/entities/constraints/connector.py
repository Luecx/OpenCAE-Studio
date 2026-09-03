from dataclasses import dataclass, field

from ...core import register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition
from .base import Constraint


CONNECTOR_TYPES = (
    "BEAM",
    "HINGE",
    "CYLINDRICAL",
    "TRANSLATOR",
    "JOIN",
    "JOINRX",
)


@register_model_type("connector_constraint")
@dataclass
class ConnectorConstraint(Constraint):
    """Connect two nodal regions with one FEMaster connector definition."""

    constraint_type: str = field(init=False, default="Connector")
    master: RegionDefinition = field(default_factory=RegionDefinition)
    slave: RegionDefinition = field(default_factory=RegionDefinition)
    connector_type: str = "BEAM"

    def __post_init__(self):
        super().__post_init__()
        self.master = as_region_definition(self.master)
        self.slave = as_region_definition(self.slave)
        self.connector_type = str(self.connector_type or "BEAM").upper()
        if self.connector_type not in CONNECTOR_TYPES:
            raise ValueError(f"Unsupported connector type '{self.connector_type}'")
