"""Regression tests for result color mapping at scalar-range boundaries."""

import numpy as np
import pyvista as pv

from opencae.ui.viewport.result_visualization import _render_scalar


def test_render_scalar_tolerates_roundoff_at_range_bounds():
    """Near-bound values use end colors while genuinely outside values stay outside."""
    grid = pv.PolyData(
        np.asarray(
            [
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (2.0, 0.0, 0.0),
                (3.0, 0.0, 0.0),
                (4.0, 0.0, 0.0),
                (5.0, 0.0, 0.0),
                (6.0, 0.0, 0.0),
            ]
        )
    )
    original = np.asarray(
        [-2.0e-9, -1.0e-12, 0.0, 0.5, 1.0, 1.0 + 1.0e-12, 1.0 + 2.0e-9]
    )
    grid.point_data["value"] = original.copy()

    display_name = _render_scalar(grid, "value", (0.0, 1.0))
    displayed = np.asarray(grid.point_data[display_name])

    # The actual result field remains exact for queries and exported values.
    assert np.array_equal(np.asarray(grid.point_data["value"]), original)

    # Roundoff at either limit is nudged into the color range.
    assert 0.0 < displayed[1] < 1.0e-6
    assert 0.0 < displayed[2] < 1.0e-6
    assert 1.0 - 1.0e-6 < displayed[4] < 1.0
    assert 1.0 - 1.0e-6 < displayed[5] < 1.0

    # Values meaningfully outside the requested range still use outside colors.
    assert displayed[0] < 0.0
    assert displayed[3] == 0.5
    assert displayed[6] > 1.0
