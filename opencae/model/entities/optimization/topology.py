from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ...core import Entity, EntityRef, register_model_type
from opencae.model.selection import (
    RegionDefinition,
    RegionSelectionItem,
    WholeModelOperand,
)


class ResponseType(StrEnum):
    VOLUME = "volume"
    VOLUME_FRACTION = "volume_fraction"
    MASS = "mass"
    MASS_FRACTION = "mass_fraction"
    STIFFNESS_ENERGY = "stiffness_energy"


class ConstraintOperator(StrEnum):
    LESS_EQUAL = "<="
    GREATER_EQUAL = ">="
    EQUAL = "="


class SymmetryType(StrEnum):
    PLANAR = "planar"
    ROTATIONAL = "rotational"


@register_model_type("topology_filter_radius")
@dataclass
class FilterRadius:
    """One radius definition used by a topology sparse operator.

    ``automatic`` uses ``factor * minimum positive nearest-neighbour distance``.
    The distance is evaluated once from the design-element centroids at run
    initialization and then frozen for the complete optimization run.
    """

    automatic: bool = True
    factor: float = 2.5
    value: float = 0.0

    def resolved(self, minimum_distance: float) -> float:
        minimum = max(float(minimum_distance), 1.0e-12)
        if self.automatic:
            return max(float(self.factor) * minimum, minimum)
        # A manual radius is intentionally not clamped to the centroid spacing.
        # Advanced users may choose a very local operator that couples only
        # coincident/symmetry-mapped centroids.
        return max(float(self.value), 1.0e-12)


@register_model_type("topology_filter_settings")
@dataclass
class TopologyFilterSettings(Entity):
    name: str = "Topology Filter"
    enabled: bool = True
    # Small matrix used to map design variables to physical densities and to
    # enforce symmetry/constraint coupling. It deliberately remains much more
    # local than the sensitivity filter.
    density_constraint_radius: FilterRadius = field(
        default_factory=lambda: FilterRadius(True, 2.5, 0.0)
    )
    # Larger matrix used only for compliance-sensitivity regularization.
    sensitivity_radius: FilterRadius = field(
        default_factory=lambda: FilterRadius(True, 5.0, 0.0)
    )
    density_weighted_sensitivities: bool = True


@register_model_type("topology_controls")
@dataclass
class TopologyControls(Entity):
    name: str = "Optimization Controls"
    maximum_iterations: int = 100
    minimum_density: float = 1.0e-3
    initial_density: float = 0.5
    simp_exponent: float = 3.0
    move_limit: float = 0.20
    density_change_tolerance: float = 5.0e-3
    objective_tolerance: float = 1.0e-3
    bisection_tolerance: float = 1.0e-8
    maximum_bisection_steps: int = 100
    save_every: int = 1
    keep_solver_files: bool = False


@register_model_type("optimization_response")
@dataclass
class OptimizationResponse(Entity):
    response_type: ResponseType | str = ResponseType.STIFFNESS_ENERGY
    region: RegionDefinition = field(default_factory=RegionDefinition)

    def __post_init__(self):
        self.response_type = ResponseType(self.response_type)
        self.region = RegionDefinition.from_values(self.region)
        if self.region.empty:
            self.region = RegionDefinition((RegionSelectionItem(WholeModelOperand()),))


@register_model_type("optimization_objective")
@dataclass
class OptimizationObjective(Entity):
    response_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="OptimizationResponse")
    )
    sense: str = "minimize"

    def __post_init__(self):
        self.sense = str(self.sense or "minimize").strip().lower()
        if self.sense != "minimize":
            raise ValueError("The topology optimizer currently supports minimize objectives only")


@register_model_type("optimization_constraint")
@dataclass
class OptimizationConstraint(Entity):
    response_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="OptimizationResponse")
    )
    operator: ConstraintOperator | str = ConstraintOperator.LESS_EQUAL
    limit: float = 0.3
    active: bool = True

    def __post_init__(self):
        self.operator = ConstraintOperator(self.operator)
        self.limit = float(self.limit)


@register_model_type("topology_symmetry")
@dataclass
class TopologySymmetry(Entity):
    symmetry_type: SymmetryType | str = SymmetryType.PLANAR
    # Resolved datum-style reference. Supported reference kinds are face,
    # datum_plane, edge and datum_vector. The dictionary stores origin,
    # direction/normal and stable source identity for previews and rebuilds.
    reference: dict = field(default_factory=dict)
    occurrences: int = 2
    enabled: bool = True

    def __post_init__(self):
        self.symmetry_type = SymmetryType(self.symmetry_type)
        self.reference = dict(self.reference or {})
        self.occurrences = max(2, int(self.occurrences))
        if self.symmetry_type == SymmetryType.PLANAR:
            self.occurrences = 2


@register_model_type("optimization_iteration")
@dataclass
class OptimizationIteration(Entity):
    number: int = 0
    objective_value: float = 0.0
    constraint_values: dict[str, float] = field(default_factory=dict)
    maximum_density_change: float = 0.0
    solver_time: float = 0.0
    density_file: str = ""
    result_file: str = ""
    converged: bool = False


@register_model_type("optimization_run")
@dataclass
class OptimizationRun(Entity):
    optimization_ref: EntityRef = field(
        default_factory=lambda: EntityRef(expected_type="TopologyOptimization")
    )
    status: str = "Prepared"
    directory: str = ""
    mesh_fingerprint: str = ""
    density_constraint_radius: float = 0.0
    sensitivity_radius: float = 0.0
    iterations: list[OptimizationIteration] = field(default_factory=list)
    message: str = ""


@register_model_type("topology_optimization")
@dataclass
class TopologyOptimization(Entity):
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
        if not self.filters:
            self.filters.append(TopologyFilterSettings())
        return self.filters[0]

    @property
    def control_settings(self) -> TopologyControls:
        if not self.controls:
            self.controls.append(TopologyControls())
        return self.controls[0]

    @property
    def objective(self) -> OptimizationObjective | None:
        return self.objectives[0] if self.objectives else None
