from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True, slots=True)
class OcUpdate:
    density: np.ndarray
    multiplier: float
    constraint_value: float
    bisection_steps: int


def optimality_criteria_update(
    density: np.ndarray,
    objective_gradient: np.ndarray,
    constraint_gradient: np.ndarray,
    *,
    design_mask: np.ndarray,
    frozen_solid: np.ndarray,
    frozen_void: np.ndarray,
    minimum_density: float,
    move_limit: float,
    constraint_limit: float,
    evaluate_constraint: Callable[[np.ndarray], float],
    tolerance: float = 1.0e-8,
    maximum_steps: int = 100,
) -> OcUpdate:
    """One OC update with a scalar resource constraint and bisection."""

    current = np.asarray(density, dtype=float).ravel()
    objective = np.asarray(objective_gradient, dtype=float).ravel()
    resource = np.asarray(constraint_gradient, dtype=float).ravel()
    design = np.asarray(design_mask, dtype=bool).ravel()
    solid = np.asarray(frozen_solid, dtype=bool).ravel()
    void = np.asarray(frozen_void, dtype=bool).ravel()
    if not (
        len(current)
        == len(objective)
        == len(resource)
        == len(design)
        == len(solid)
        == len(void)
    ):
        raise ValueError("OC arrays must have matching lengths")
    if np.any(solid & void):
        raise ValueError("Frozen-solid and frozen-void regions overlap")

    active = design & ~solid & ~void
    if not np.any(active):
        raise ValueError("The topology design domain has no free elements")
    if np.any(~np.isfinite(objective[active])) or np.any(~np.isfinite(resource[active])):
        raise ValueError("OC gradients contain NaN or infinity")
    if np.any(resource[active] <= 0.0):
        raise ValueError("The active resource-constraint gradient must be positive")

    lower_bound = max(float(minimum_density), 1.0e-9)
    upper_bound = 1.0
    move = max(float(move_limit), 1.0e-6)
    l1 = 0.0
    l2 = 1.0e9
    best = current.copy()
    best_value = float(evaluate_constraint(best))
    best_multiplier = l2
    steps = 0

    for steps in range(1, max(int(maximum_steps), 1) + 1):
        multiplier = 0.5 * (l1 + l2)
        ratio = np.maximum(
            -objective[active] / np.maximum(multiplier * resource[active], 1.0e-300),
            1.0e-30,
        )
        trial = current.copy()
        proposed = current[active] * np.sqrt(ratio)
        proposed = np.minimum(current[active] + move, proposed)
        proposed = np.maximum(current[active] - move, proposed)
        trial[active] = np.clip(proposed, lower_bound, upper_bound)
        trial[solid] = upper_bound
        trial[void] = lower_bound
        trial[~design & ~solid & ~void] = current[~design & ~solid & ~void]
        value = float(evaluate_constraint(trial))
        best = trial
        best_value = value
        best_multiplier = multiplier
        if value > float(constraint_limit):
            l1 = multiplier
        else:
            l2 = multiplier
        scale = max(1.0, abs(l1) + abs(l2))
        if (l2 - l1) / scale <= float(tolerance):
            break

    return OcUpdate(best, best_multiplier, best_value, steps)
