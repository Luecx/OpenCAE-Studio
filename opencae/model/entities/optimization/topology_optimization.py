"""Defines the aggregate study containing one topology optimization setup."""

from dataclasses import dataclass, field

from opencae.model.selection import (
    RegionDefinition,
    RegionSelectionItem,
    WholeModelOperand,
)

from ...core import EntityRef, register_model_type
from ..studies import Study
from .optimization_constraint import OptimizationConstraint
from .optimization_objective import OptimizationObjective
from .optimization_response import OptimizationResponse
from .optimization_run import OptimizationRun
from .topology_controls import TopologyControls
from .topology_filter_settings import TopologyFilterSettings
from .topology_symmetry import TopologySymmetry


@register_model_type("topology_optimization")
@dataclass
class TopologyOptimization(Study):
    """Topology study definition, regularization, controls and run history."""

    study_type: str = field(init=False, default="Topology Optimization")
    analysis_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="Analysis")
    )
    design_domain: RegionDefinition = field(default_factory=RegionDefinition)
    frozen_solid: RegionDefinition = field(default_factory=RegionDefinition)
    frozen_void: RegionDefinition = field(default_factory=RegionDefinition)
    responses: list[OptimizationResponse] = field(default_factory=list)
    objectives: list[OptimizationObjective] = field(default_factory=list)
    constraints: list[OptimizationConstraint] = field(default_factory=list)
    filters: list[TopologyFilterSettings] = field(default_factory=list)
    symmetries: list[TopologySymmetry] = field(default_factory=list)
    controls: list[TopologyControls] = field(default_factory=list)
    runs: list[OptimizationRun] = field(default_factory=list)

    def __post_init__(self):
        self.design_domain = RegionDefinition.from_values(self.design_domain)
        self.frozen_solid = RegionDefinition.from_values(self.frozen_solid)
        self.frozen_void = RegionDefinition.from_values(self.frozen_void)
        if self.design_domain.empty:
            self.design_domain = RegionDefinition(
                (RegionSelectionItem(WholeModelOperand()),)
            )
        if not self.filters:
            self.filters.append(TopologyFilterSettings())
        if not self.controls:
            self.controls.append(TopologyControls())

    @property
    def filter_settings(self) -> TopologyFilterSettings:
        """Return the active filter settings, repairing legacy empty collections."""

        if not self.filters:
            self.filters.append(TopologyFilterSettings())
        return self.filters[0]

    @property
    def control_settings(self) -> TopologyControls:
        """Return the active controls, repairing legacy empty collections."""

        if not self.controls:
            self.controls.append(TopologyControls())
        return self.controls[0]

    @property
    def objective(self) -> OptimizationObjective | None:
        """Return the currently active single objective."""

        return self.objectives[0] if self.objectives else None
