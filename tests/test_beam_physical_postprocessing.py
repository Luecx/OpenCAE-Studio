"""Regression tests for lazy physical-beam postprocessing primitives."""

from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.profiles import GraphProfile, RectangleProfile
from opencae.model.entities.profiles.section_geometry import section_patches
from opencae.results.beam_physical_representation import BeamPhysicalRepresentation
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


def _simple_representation():
    return BeamPhysicalRepresentation(
        cells=np.asarray((4, 2, 3, 5, 4), dtype=np.int64),
        celltypes=np.asarray((9,), dtype=np.uint8),
        cell_source=np.asarray((0,), dtype=np.int64),
        source_point_count=2,
        source_node_ids=np.asarray((1, 2), dtype=np.int64),
        source_element_ids=np.asarray((7,), dtype=np.int64),
        generated_source_a=np.asarray((0, 0, 0, 0), dtype=np.int64),
        generated_source_b=np.asarray((1, 1, 1, 1), dtype=np.int64),
        generated_xi=np.asarray((0.0, 0.0, 1.0, 1.0), dtype=float),
        generated_offset=np.asarray(
            ((0.0, 1.0, 0.0), (0.0, -1.0, 0.0),
             (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)),
            dtype=float,
        ),
        generated_stress_coefficients=np.zeros((4, 3), dtype=float),
        generated_solver_element_ids=np.full(4, 7, dtype=np.int64),
    )


def _simple_source_grid():
    source = pv.UnstructuredGrid(
        np.asarray((2, 0, 1), dtype=np.int64),
        np.asarray((3,), dtype=np.uint8),
        np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
    )
    source.point_data["node_id"] = np.asarray((1, 2), dtype=np.int64)
    source.cell_data["element_id"] = np.asarray((7,), dtype=np.int64)
    return source


def test_expanded_beam_points_receive_translation_plus_rotation_cross_offset():
    source = _simple_source_grid()
    for key in ("DISP:D1", "DISP:D2", "DISP:D3"):
        source.point_data[key] = np.zeros(2, dtype=float)
    source.point_data["DISP:D4"] = np.zeros(2, dtype=float)
    source.point_data["DISP:D5"] = np.zeros(2, dtype=float)
    source.point_data["DISP:D6"] = np.ones(2, dtype=float)

    expanded = _simple_representation().expand(source)

    np.testing.assert_allclose(
        expanded.point_data["DISP:D1"][2:],
        (-1.0, 1.0, -1.0, 1.0),
    )
    np.testing.assert_allclose(expanded.point_data["DISP:D2"][2:], 0.0)
    np.testing.assert_allclose(expanded.point_data["DISP:D3"][2:], 0.0)
    np.testing.assert_allclose(
        expanded.point_data["_opencae_beam_xi"][2:],
        (0.0, 0.0, 1.0, 1.0),
    )


def test_selected_stress_is_recovered_onto_physical_beam_surface():
    source = _simple_source_grid()
    source.point_data["STRESS:SXX"] = np.zeros(2, dtype=float)
    representation = _simple_representation()
    representation.generated_stress_coefficients[:, 0] = 0.5
    forces = {
        7: np.asarray(
            (
                (10.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                (30.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            ),
            dtype=float,
        )
    }

    expanded = representation.expand(
        source,
        "STRESS:SXX",
        element_nodal_forces=forces,
    )

    np.testing.assert_allclose(
        expanded.point_data["STRESS:SXX"][2:],
        (5.0, 5.0, 15.0, 15.0),
    )
    np.testing.assert_allclose(
        expanded.point_data["BEAM:Normal Stress"][2:],
        (5.0, 5.0, 15.0, 15.0),
    )


def test_missing_selected_stress_array_is_created_for_physical_beams():
    source = _simple_source_grid()
    representation = _simple_representation()
    representation.generated_stress_coefficients[:, 0] = 0.5
    forces = {
        7: np.asarray(
            (
                (10.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                (30.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            ),
            dtype=float,
        )
    }

    expanded = representation.expand(
        source,
        "STRESS:SXX",
        element_nodal_forces=forces,
    )

    assert "STRESS:SXX" in expanded.point_data
    assert np.all(np.isnan(expanded.point_data["STRESS:SXX"][:2]))
    np.testing.assert_allclose(
        expanded.point_data["STRESS:SXX"][2:],
        (5.0, 5.0, 15.0, 15.0),
    )


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


def test_res_section_force_parser_maps_frd_step_to_res_loadcase_order(tmp_path):
    path = tmp_path / "beam.res"
    path.write_text(
        """LC 10
FIELD, NAME=LOCAL_SECTION_FORCES, TYPE=ELEMENT_NODAL, INDEX_COLS=2, VALUE_COLS=6, ROWS=2
17 0 10 0 0 0 0 0
17 1 20 0 0 0 0 0
END FIELD
LC 20
FIELD, NAME=LOCAL_SECTION_FORCES, TYPE=ELEMENT_NODAL, INDEX_COLS=2, VALUE_COLS=6, ROWS=2
17 0 30 0 0 0 0 0
17 1 40 0 0 0 0 0
END FIELD
"""
    )

    forces = load_local_section_forces(path, step_id=2)

    np.testing.assert_allclose(forces[17][:, 0], (30.0, 40.0))


def test_res_section_force_parser_uses_single_unambiguous_loadcase(tmp_path):
    path = tmp_path / "beam.res"
    path.write_text(
        """LC 7
FIELD, NAME=LOCAL_SECTION_FORCES, TYPE=ELEMENT_NODAL, INDEX_COLS=2, VALUE_COLS=6, ROWS=2
17 0 12 0 0 0 0 0
17 1 24 0 0 0 0 0
END FIELD
"""
    )

    forces = load_local_section_forces(path, step_id=1)

    np.testing.assert_allclose(forces[17][:, 0], (12.0, 24.0))
