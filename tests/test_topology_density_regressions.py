"""Regression tests for topology density I/O, OC redistribution and display thresholds."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from opencae.optimization.iteration import read_topology_fields
from opencae.optimization.oc import optimality_criteria_update
from opencae.ui.viewport.topology_overlay import visible_density_indices


def _write_topology_res(path: Path, density_values):
    rows = len(density_values) + 1
    blocks = []
    for name, values in (
        ("COMPLIANCE", [0.0, *([1.0] * len(density_values))]),
        ("DENS_GRAD", [0.0, *([-1.0] * len(density_values))]),
        ("VOLUME", [0.0, *([1.0] * len(density_values))]),
        ("DENSITY", [0.0, *density_values]),
    ):
        lines = [
            f"FIELD, NAME={name}, TYPE=ELEMENT, COLS=1, ROWS={rows}",
            *(f"{float(value):.7e}" for value in values),
            "END FIELD",
        ]
        blocks.extend(lines)
    path.write_text("LC 1\n" + "\n".join(blocks) + "\n", encoding="utf-8")


def test_femaster_text_rounding_does_not_reject_nonuniform_density(tmp_path):
    expected = np.asarray([0.123456789, 0.876543219], dtype=float)
    path = tmp_path / "rounded.res"
    _write_topology_res(path, [0.1234568, 0.8765432])
    index = SimpleNamespace(solver_ids=np.asarray([1, 2], dtype=np.int64))

    fields = read_topology_fields(path, index, expected)

    assert np.allclose(fields["DENSITY"], [0.1234568, 0.8765432])


def test_femaster_density_validation_still_rejects_real_mismatch(tmp_path):
    expected = np.asarray([0.123456789, 0.876543219], dtype=float)
    path = tmp_path / "mismatch.res"
    _write_topology_res(path, [0.2, 0.8765432])
    index = SimpleNamespace(solver_ids=np.asarray([1, 2], dtype=np.int64))

    with pytest.raises(ValueError, match="solver element 1"):
        read_topology_fields(path, index, expected)


def test_oc_redistributes_material_from_a_uniform_feasible_state():
    density = np.full(4, 0.3)
    objective_gradient = np.asarray([-4.0, -3.0, -2.0, -1.0])
    constraint_gradient = np.full(4, 0.25)

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
    assert float(np.ptp(result.density)) > 0.1


def test_threshold_keeps_uniform_values_with_roundoff_visible():
    values = np.asarray([0.3 - 5.0e-10, 0.3 + 5.0e-10, 0.29999, np.nan])

    visible = visible_density_indices(values, 0.3)

    assert np.array_equal(visible, np.asarray([0, 1]))
