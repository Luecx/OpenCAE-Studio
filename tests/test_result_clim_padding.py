"""Regression coverage for contour limits around exact result extrema."""

from types import SimpleNamespace

import numpy as np

from opencae.ui.other.viewport.result_visualization import _clim


def _grid(values):
    return SimpleNamespace(
        point_data={"STRESS:S11": np.asarray(values, dtype=float)},
        cell_data={},
    )


def test_clim_pads_auto_range_by_one_part_per_million():
    grid = _grid((-2.0, 8.0))

    minimum, maximum = _clim(grid, "STRESS:S11", {})

    assert np.isclose(minimum, -2.00001)
    assert np.isclose(maximum, 8.00001)


def test_clim_pads_explicit_range_too():
    grid = _grid((-2.0, 8.0))
    settings = {
        "minimum": -5.0,
        "maximum": 15.0,
        "minimum_auto": False,
        "maximum_auto": False,
    }

    minimum, maximum = _clim(grid, "STRESS:S11", settings)

    assert np.isclose(minimum, -5.00002)
    assert np.isclose(maximum, 15.00002)
