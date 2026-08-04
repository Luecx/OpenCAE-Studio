"""Evaluates one topology iteration and prepares the next OC density update."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .oc import optimality_criteria_update
from .res_field_reader import ResFieldReader
from .res_values import dense_values
from .responses import evaluate_response

_REQUIRED_FIELDS = {"COMPLIANCE", "DENS_GRAD", "VOLUME", "DENSITY"}

# FEMaster's ResWriter enables scientific formatting but keeps the C++ stream
# default precision. Arbitrary densities therefore round to about seven
# significant decimal digits in the text .res file.
_DENSITY_RELATIVE_TOLERANCE = 2.0e-6
_DENSITY_ABSOLUTE_TOLERANCE = 5.0e-9


@dataclass(frozen=True, slots=True)
class IterationComputation:
    """Numerical outcome of one completed topology solver evaluation."""

    objective_value: float
    constraint_value: float
    constraint_id: str
    next_design_density: np.ndarray
    next_physical_density: np.ndarray
    maximum_change: float
    relative_objective_change: float
    converged: bool


def read_topology_fields(path, index, expected_density, reader=None):
    """Read and validate the FEMaster fields required by the optimizer."""

    fields = (reader or ResFieldReader()).read_fields(
        path,
        names=_REQUIRED_FIELDS,
    )
    values = {
        name: dense_values(fields[name], index.solver_ids)[:, 0]
        for name in _REQUIRED_FIELDS
    }
    _validate_returned_density(
        values["DENSITY"],
        expected_density,
        index.solver_ids,
    )
    return values


def _validate_returned_density(returned, expected, solver_ids):
    """Check FEMaster's rounded text output against the submitted density."""

    actual = np.asarray(returned, dtype=float).ravel()
    submitted = np.asarray(expected, dtype=float).ravel()
    ids = np.asarray(solver_ids, dtype=np.int64).ravel()
    if actual.shape != submitted.shape or actual.shape != ids.shape:
        raise ValueError(
            "FEMaster returned a DENSITY field with a different element count "
            "than the submitted design"
        )
    if not np.all(np.isfinite(actual)) or not np.all(np.isfinite(submitted)):
        raise ValueError(
            "FEMaster returned a DENSITY field containing NaN or infinity"
        )

    difference = np.abs(actual - submitted)
    allowance = (
        _DENSITY_ABSOLUTE_TOLERANCE
        + _DENSITY_RELATIVE_TOLERANCE * np.abs(submitted)
    )
    mismatch = difference > allowance
    if not np.any(mismatch):
        return

    normalized = difference / np.maximum(allowance, np.finfo(float).tiny)
    worst = int(np.argmax(normalized))
    relative = difference[worst] / max(
        abs(submitted[worst]),
        _DENSITY_ABSOLUTE_TOLERANCE,
    )
    raise ValueError(
        "FEMaster returned a DENSITY field that does not match the submitted "
        f"design at solver element {int(ids[worst])}: "
        f"submitted={submitted[worst]:.12g}, returned={actual[worst]:.12g}, "
        f"absolute difference={difference[worst]:.3g}, "
        f"relative difference={relative:.3g}"
    )


def compute_iteration(
    project,
    optimization,
    index,
    masks,
    operators,
    design_density,
    physical_density,
    previous_objective,
    fields,
):
    """Evaluate responses, filter gradients and run one OC/bisection update."""

    controls = optimization.control_settings
    volumes = fields["VOLUME"]
    compliance = fields["COMPLIANCE"]
    density_gradient = fields["DENS_GRAD"]
    objective_response = project.resolve(optimization.objective.response_ref)
    objective = evaluate_response(
        objective_response,
        masks[objective_response.id],
        density=physical_density,
        volumes=volumes,
        compliance=compliance,
        density_gradient=density_gradient,
        material_densities=index.material_densities,
    )
    constraint = next(item for item in optimization.constraints if item.active)
    constraint_response = project.resolve(constraint.response_ref)
    resource = evaluate_response(
        constraint_response,
        masks[constraint_response.id],
        density=physical_density,
        volumes=volumes,
        compliance=compliance,
        density_gradient=density_gradient,
        material_densities=index.material_densities,
    )
    objective_gradient = operators.sensitivity_gradient(
        objective.gradient,
        physical_density,
        density_weighted=(
            optimization.filter_settings.density_weighted_sensitivities
        ),
        minimum_density=controls.minimum_density,
    )
    resource_gradient = operators.constraint_gradient(resource.gradient)
    fixed = (
        ~masks["design"]
        | masks["frozen_solid"]
        | masks["frozen_void"]
    )
    objective_gradient[fixed] = 0.0
    resource_gradient[fixed] = 0.0

    def physical(candidate):
        result = np.clip(
            operators.physical_density(np.asarray(candidate, dtype=float)),
            controls.minimum_density,
            1.0,
        )
        result[~masks["design"]] = 1.0
        result[masks["frozen_solid"]] = 1.0
        result[masks["frozen_void"]] = controls.minimum_density
        return result

    def constraint_value(candidate):
        return evaluate_response(
            constraint_response,
            masks[constraint_response.id],
            density=physical(candidate),
            volumes=volumes,
            compliance=compliance,
            density_gradient=density_gradient,
            material_densities=index.material_densities,
        ).value

    free = (
        masks["design"]
        & ~masks["frozen_solid"]
        & ~masks["frozen_void"]
    )
    minimum_candidate = np.asarray(design_density, dtype=float).copy()
    minimum_candidate[free] = controls.minimum_density
    minimum_value = constraint_value(minimum_candidate)
    if minimum_value > constraint.limit * (1.0 + 1.0e-8):
        raise ValueError(
            "The resource constraint is infeasible: its minimum reachable value "
            f"is {minimum_value:.8g}, above the limit {constraint.limit:.8g}"
        )
    update = optimality_criteria_update(
        design_density,
        objective_gradient,
        resource_gradient,
        design_mask=masks["design"],
        frozen_solid=masks["frozen_solid"],
        frozen_void=masks["frozen_void"],
        minimum_density=controls.minimum_density,
        move_limit=controls.move_limit,
        constraint_limit=constraint.limit,
        evaluate_constraint=constraint_value,
        tolerance=controls.bisection_tolerance,
        maximum_steps=controls.maximum_bisection_steps,
    )
    maximum_change = float(
        np.max(np.abs(update.density - design_density)[masks["design"]])
    )
    relative_change = (
        np.inf
        if previous_objective is None
        else abs(objective.value - previous_objective)
        / max(abs(previous_objective), 1.0)
    )
    converged = bool(
        maximum_change <= controls.density_change_tolerance
        and relative_change <= controls.objective_tolerance
        and resource.value <= constraint.limit * (1.0 + 1.0e-6)
    )
    return IterationComputation(
        objective.value,
        resource.value,
        constraint.id,
        update.density,
        physical(update.density),
        maximum_change,
        float(relative_change),
        converged,
    )
