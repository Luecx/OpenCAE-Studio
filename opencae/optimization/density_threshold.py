"""Chooses topology display thresholds matching an active resource constraint."""

from __future__ import annotations

import numpy as np

from opencae.model.entities.optimization import (
    OptimizationRun,
    ResponseType,
    TopologyOptimization,
)

_FRACTION_TYPES = {ResponseType.VOLUME_FRACTION, ResponseType.MASS_FRACTION}
_MASS_TYPES = {ResponseType.MASS, ResponseType.MASS_FRACTION}


def automatic_density_threshold(
    project,
    run,
    mesh_index,
    density,
    volumes=None,
) -> tuple[float, float, float] | None:
    """Return threshold, achieved binary resource value, and constraint limit.

    Every distinct density is an exact visibility breakpoint. Evaluating those
    weighted breakpoints finds the closest feasible visual mass/volume without
    the approximation and stopping tolerance of numeric bisection.
    """
    context = _constraint_context(project, run)
    if context is None:
        return None
    constraint, response = context
    values = np.asarray(density, dtype=float).ravel()
    if len(values) != mesh_index.count:
        return None
    selected = mesh_index.mask_for(project, response.region)
    weights = _resource_weights(response.response_type, mesh_index, volumes)
    valid = selected & np.isfinite(values) & np.isfinite(weights) & (weights > 0.0)
    if not np.any(valid):
        return None

    visible_density = values[valid]
    visible_weights = weights[valid]
    kind = ResponseType(response.response_type)
    reference = float(np.sum(visible_weights))
    limit = float(constraint.limit)
    target = limit * reference if kind in _FRACTION_TYPES else limit
    threshold, resource = _closest_weighted_breakpoint(
        visible_density,
        visible_weights,
        target,
    )
    achieved = resource / reference if kind in _FRACTION_TYPES else resource
    return threshold, achieved, limit


def active_constraint_limit(project, run) -> float | None:
    """Return the active constraint limit associated with one optimization run."""
    context = _constraint_context(project, run)
    return float(context[0].limit) if context is not None else None


def _constraint_context(project, run):
    """Resolve the active constraint and its resource response for one run."""
    if not isinstance(run, OptimizationRun):
        return None
    study = project.try_resolve(run.optimization_ref)
    if not isinstance(study, TopologyOptimization):
        study = project.try_resolve(project.index.parent_id.get(run.id))
    if not isinstance(study, TopologyOptimization):
        return None
    constraint = next((item for item in study.constraints if item.active), None)
    response = (
        project.try_resolve(constraint.response_ref)
        if constraint is not None
        else None
    )
    return (constraint, response) if response is not None else None


def _resource_weights(response_type, mesh_index, volumes) -> np.ndarray:
    """Return per-element volume or mass weights for binary visualization."""
    volume_values = (
        np.asarray(volumes, dtype=float).ravel()
        if volumes is not None
        else np.ones(mesh_index.count, dtype=float)
    )
    if len(volume_values) != mesh_index.count:
        volume_values = np.ones(mesh_index.count, dtype=float)
    if ResponseType(response_type) not in _MASS_TYPES:
        return volume_values
    material = np.asarray(mesh_index.material_densities, dtype=float).ravel()
    return volume_values * material


def _closest_weighted_breakpoint(density, weights, target) -> tuple[float, float]:
    """Choose the all-or-nothing density cutoff closest to a target resource."""
    order = np.argsort(-density, kind="stable")
    sorted_density = density[order]
    cumulative = np.cumsum(weights[order])
    group_ends = np.flatnonzero(
        np.r_[sorted_density[1:] != sorted_density[:-1], True]
    )
    resources = np.r_[0.0, cumulative[group_ends]]
    choice = int(np.argmin(np.abs(resources - float(target))))
    if choice == 0:
        return float(np.nextafter(sorted_density[0], np.inf)), 0.0
    return float(sorted_density[group_ends[choice - 1]]), float(resources[choice])
