"""Regression tests for lazy physical-beam postprocessing primitives."""

from __future__ import annotations

import numpy as np

from opencae.model.entities.profiles import GraphProfile, RectangleProfile
from opencae.model.entities.profiles.section_geometry import section_patches
from opencae.results.beam_physical_stress import (
    recover_normal_stress,
    stress_coefficients,
)
from opencae.results.femaster_res_section_forces import load_local_section_forces


def test_rectangle_section_geometry_is_centered_on_profile_centroid():
    profile = RectangleProfile(
        name="R",
        dimensions={"width": 4.0, "height": 2.0},
    )

    patches = section_patches(profile)

    assert len(patches) == 1
    np.testing.assert_allclose(
        patches[0],
        np.asarray(
            ((-2.0, -1.0), (2.0, -1.0), (2.0, 1.0), (-2.0, 1.0))
        ),
    )


def test_graph_profile_segments_become_thickness_patches():
    profile = GraphProfile(
        name="Graph",
        dimensions={
            "nodes": "1,-2,0\n2,2,0",
            "segments": "1,2,1.0",
        },
    )

    patches = section_patches(profile)

    assert len(patches) == 1
    assert patches[0].shape == (4, 2)
    np.testing.assert_allclose(np.ptp(patches[0][:, 0]), 4.0)
    np.testing.assert_allclose(np.ptp(patches[0][:, 1]), 1.0)


def test_stress_coefficients_reduce_to_axial_plus_uncoupled_bending():
    properties = {
        "Area": 8.0,
        "Iyy": 2.0,
        "Izz": 4.0,
        "Iyz": 0.0,
    }

    axial, my, mz = stress_coefficients(properties, y=2.0, z=1.0)

    assert axial == 1.0 / 8.0
    assert my == -1.0 / 2.0
    assert mz == 2.0 / 4.0


def test_section_force_recovery_interpolates_beam_end_resultants():
    coefficients = np.asarray(
        (
            (0.5, 0.0, 0.0),
            (0.5, 0.0, 0.0),
            (0.5, 0.0, 0.0),
        ),
        dtype=float,
    )
    forces = {
        7: np.asarray(
            (
                (10.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                (30.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            )
        )
    }

    recovered = recover_normal_stress(
        object(),
        np.asarray((0, 0, 0), dtype=np.int64),
        np.asarray((1, 1, 1), dtype=np.int64),
        np.asarray((0.0, 0.5, 1.0), dtype=float),
        coefficients,
        solver_element_ids=np.asarray((7, 7, 7), dtype=np.int64),
        element_nodal_forces=forces,
    )

    np.testing.assert_allclose(recovered, (5.0, 10.0, 15.0))


def test_res_section_force_parser_preserves_local_endpoint_order(tmp_path):
    path = tmp_path / "beam.res"
    path.write_text(
        """LC 2
FIELD, NAME=LOCAL_SECTION_FORCES, TYPE=ELEMENT_NODAL, INDEX_COLS=2, VALUE_COLS=6, ROWS=2
              17               0    1.000000e+01    2.000000e+00    3.000000e+00    4.000000e+00    5.000000e+00    6.000000e+00
              17               1    2.000000e+01    7.000000e+00    8.000000e+00    9.000000e+00    1.000000e+01    1.100000e+01
END FIELD
"""
    )

    forces = load_local_section_forces(path, step_id=2)

    assert set(forces) == {17}
    assert forces[17].shape == (2, 6)
    np.testing.assert_allclose(forces[17][0], (10, 2, 3, 4, 5, 6))
    np.testing.assert_allclose(forces[17][1], (20, 7, 8, 9, 10, 11))
