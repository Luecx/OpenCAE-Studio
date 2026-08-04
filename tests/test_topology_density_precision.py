"""Regression tests for topology density precision and thresholding."""

import numpy as np
import pytest

from opencae.optimization.iteration import _validate_returned_density
from opencae.optimization.oc import optimality_criteria_update
from opencae.ui.viewport.topology_overlay import visible_density_indices


def test_density_echo_accepts_femaster_res_writer_rounding():
    expected = np.asarray(
        [0.3, 0.123456789012, 0.987654321098, 0.00123456789012],
        dtype=float,
    )
    returned = np.asarray(
        [float(f"{value:.6e}") for value in expected],
        dtype=float,
    )

    _validate_returned_density(
        returned,
        expected,
        np.asarray([1, 2, 3, 4], dtype=np.int64),
    )


def test_density_echo_rejects_a_real_solver_mapping_mismatch():
    expected = np.asarray([0.3, 0.25, 0.2], dtype=float)
    returned = np.asarray([0.3, 0.2, 0.2], dtype=float)

    with pytest.raises(ValueError, match="solver element 2"):
        _validate_returned_density(
            returned,
            expected,
            np.asarray([1, 2, 3], dtype=np.int64),
        )


def test_oc_redistributes_a_uniform_feasible_density():
    density = np.full(4, 0.3, dtype=float)
    objective_gradient = np.asarray([-4.0, -3.0, -2.0, -1.0])
    constraint_gradient = np.full(4, 0.25, dtype=float)

    result = optimality_criteria_update(
        density,
        objective_gradient,
        constraint_gradient,
        design_mask=np.ones(4, dtype=bool),
        frozen_solid=np.zeros(4, dtype=bool),
        frozen_void=np.zeros(4, dtype=bool),
        minimum_density=1.0e-3,
        move_limit=0.2,
        constraint_limit=0.3,
        evaluate_constraint=lambda value: float(np.mean(value)),
        tolerance=1.0e-10,
        maximum_steps=200,
    )

    assert float(np.mean(result.density)) <= 0.300001
    assert result.density[0] > result.density[-1]
    assert float(np.ptp(result.density)) > 0.1


def test_density_threshold_keeps_values_at_limit_with_float_noise():
    density = np.asarray(
        [
            0.3,
            np.nextafter(0.3, -np.inf),
            0.2999999995,
            0.299,
            np.nan,
        ],
        dtype=float,
    )

    visible = visible_density_indices(density, 0.3)

    assert np.array_equal(visible, np.asarray([0, 1, 2]))
