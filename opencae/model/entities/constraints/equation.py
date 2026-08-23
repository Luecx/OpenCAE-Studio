"""Model linear equation constraints as explicit target/DOF/coefficient terms."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...core import register_model_type
from opencae.model.selection import RegionDefinition, as_region_definition
from .base import Constraint


@register_model_type("equation_term")
@dataclass
class EquationTerm:
    """Represent one target degree of freedom in a linear constraint equation."""

    target: RegionDefinition = field(default_factory=RegionDefinition)
    dof: int = 1
    coefficient: float = 1.0

    def __post_init__(self) -> None:
        """Normalize the selected target and enforce a physical DOF index."""
        self.target = as_region_definition(self.target)
        self.dof = int(self.dof)
        self.coefficient = float(self.coefficient)
        if not 1 <= self.dof <= 6:
            raise ValueError("Equation term DOF must be between 1 and 6")


@register_model_type("equation_constraint")
@dataclass
class EquationConstraint(Constraint):
    """Constrain a linear combination of selected solver degrees of freedom."""

    constraint_type: str = field(init=False, default="Equation")
    master: RegionDefinition = field(default_factory=RegionDefinition)
    slave: RegionDefinition = field(default_factory=RegionDefinition)
    terms: list[EquationTerm] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize region endpoints and every explicit equation term."""
        super().__post_init__()
        self.master = as_region_definition(self.master)
        self.slave = as_region_definition(self.slave)
        self.terms = [
            term if isinstance(term, EquationTerm) else EquationTerm(**term)
            for term in self.terms
        ]
