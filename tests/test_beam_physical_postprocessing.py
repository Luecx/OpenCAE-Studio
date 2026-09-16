"""Regression tests for physical-beam geometry and stress reconstruction."""

from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.profiles import BoxProfile, GraphProfile, RectangleProfile
from opencae.model.entities.profiles.section_geometry import section_patches
from opencae.results.beam_physical_representation import BeamPhysicalRepresentation
from opencae.results.beam_physical_stress import recover_normal_stress, stress_coefficients


def _patch_area(patch):
    y = np.asarray(patch)[:, 0]
    z = np.asarray(patch)[:, 1]
    return 0.5 * abs(float(np.sum(y * np.roll(z, -1) - z * np.roll(y, -1))))


def test_rectangle_section_geometry_uses_four_segments_and_stays_centered():
    profile = RectangleProfile(name="R", dimensions={"width": 4.0, "height": 2.0})
    patches = section_patches(profile)
    assert len(patches) == 4
    assert all(patch.shape == (4, 2) for patch in patches)
    np.testing.assert_allclose(sum(_patch_area(patch) for patch in patches), 8.0)
    points = np.vstack(patches)
    np.testing.assert_allclose(points[:, 0].min(), -2.0)
    np.testing.assert_allclose(points[:, 0].max(), 2.0)
    np.testing.assert_allclose(points[:, 1].min(), -1.0)
    np.testing.assert_allclose(points[:, 1].max(), 1.0)


def test_box_section_has_four_corner_blocks_and_sixteen_wall_segments():
    profile = BoxProfile(
        name="Box",
        dimensions={"width": 10.0, "height": 6.0, "thickness": 1.0},
    )
    patches = section_patches(profile)
    assert len(patches) == 20
    np.testing.assert_allclose(sum(_patch_area(patch) for patch in patches), 28.0)
    corners = [
        patch
        for patch in patches
        if np.all(np.abs(patch[:, 0]) >= 4.0 - 1.0e-12)
        and np.all(np.abs(patch[:, 1]) >= 2.0 - 1.0e-12)
    ]
    assert len(corners) == 4
    for corner in corners:
        np.testing.assert_allclose(np.ptp(corner[:, 0]), 1.0)
        np.testing.assert_allclose(np.ptp(corner[:, 1]), 1.0)


def test_graph_profile_segments_become_four_thickness_patches():
    profile = GraphProfile(
        name="Graph",
        dimensions={"nodes": "1,-2,0\n2,2,0", "segments": "1,2,1.0"},
    )
    patches = section_patches(profile)
    assert len(patches) == 4
    for patch in patches:
        assert patch.shape == (4, 2)
        np.testing.assert_allclose(np.ptp(patch[:, 0]), 1.0)
        np.testing.assert_allclose(np.ptp(patch[:, 1]), 1.0)
    np.testing.assert_allclose(sum(_patch_area(patch) for patch in patches), 4.0)


def test_stress_coefficients_follow_femaster_uncoupled_bending_signs():
    axial, m2, m3 = stress_coefficients(
        {"Area": 8.0, "Iyy": 2.0, "Izz": 4.0, "Iyz": 0.0},
        y=2.0,
        z=1.0,
    )
    assert axial == 1.0 / 8.0
    assert m2 == 1.0 / 2.0
    assert m3 == -2.0 / 4.0


def test_stress_coefficients_include_coupled_i23_bending():
    axial, m2, m3 = stress_coefficients(
        {"Area": 10.0, "Iyy": 5.0, "Izz": 8.0, "Iyz": 2.0},
        y=3.0,
        z=-1.0,
    )
    determinant = 5.0 * 8.0 - 2.0**2
    assert axial == 0.1
    np.testing.assert_allclose(m2, (8.0 * -1.0 - 2.0 * 3.0) / determinant)
    np.testing.assert_allclose(m3, (2.0 * -1.0 - 5.0 * 3.0) / determinant)


def test_section_force_recovery_interpolates_beam_end_resultants():
    coefficients = np.asarray(
        ((0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 0.0, 0.0)),
        dtype=float,
    )
    forces = {
        7: np.asarray(
            ((10.0, 0, 0, 0, 0, 0), (30.0, 0, 0, 0, 0, 0)),
            dtype=float,
        )
    }
    recovered = recover_normal_stress(
        object(),
        np.asarray((0, 0, 0), dtype=np.int64),
        np.asarray((1, 1, 1), dtype=np.int64),
        np.asarray((0.0, 0.5, 1.0)),
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
        generated_xi=np.asarray((0.0, 0.0, 1.0, 1.0)),
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
        source.point_data[key] = np.zeros(2)
    source.point_data["DISP:D4"] = np.zeros(2)
    source.point_data["DISP:D5"] = np.zeros(2)
    source.point_data["DISP:D6"] = np.ones(2)
    expanded = _simple_representation().expand(source)
    np.testing.assert_allclose(expanded.point_data["DISP:D1"][2:], (-1, 1, -1, 1))
    np.testing.assert_allclose(expanded.point_data["DISP:D2"][2:], 0.0)
    np.testing.assert_allclose(expanded.point_data["DISP:D3"][2:], 0.0)
    np.testing.assert_allclose(expanded.point_data["_opencae_beam_xi"][2:], (0, 0, 1, 1))


def test_selected_stress_is_recovered_onto_physical_beam_surface():
    source = _simple_source_grid()
    source.point_data["STRESS:SXX"] = np.zeros(2)
    representation = _simple_representation()
    representation.generated_stress_coefficients[:, 0] = 0.5
    forces = {
        7: np.asarray(((10, 0, 0, 0, 0, 0), (30, 0, 0, 0, 0, 0)), dtype=float)
    }
    expanded = representation.expand(
        source,
        "STRESS:SXX",
        element_nodal_forces=forces,
    )
    np.testing.assert_allclose(
        expanded.point_data["STRESS:SXX"][2:], (5.0, 5.0, 15.0, 15.0)
    )
    np.testing.assert_allclose(
        expanded.point_data["BEAM:Normal Stress"][2:], (5.0, 5.0, 15.0, 15.0)
    )


def test_missing_selected_stress_array_is_created_for_physical_beams():
    source = _simple_source_grid()
    representation = _simple_representation()
    representation.generated_stress_coefficients[:, 0] = 0.5
    forces = {
        7: np.asarray(((10, 0, 0, 0, 0, 0), (30, 0, 0, 0, 0, 0)), dtype=float)
    }
    expanded = representation.expand(
        source,
        "STRESS:SXX",
        element_nodal_forces=forces,
    )
    assert "STRESS:SXX" in expanded.point_data
    assert np.all(np.isnan(expanded.point_data["STRESS:SXX"][:2]))
    np.testing.assert_allclose(
        expanded.point_data["STRESS:SXX"][2:], (5.0, 5.0, 15.0, 15.0)
    )