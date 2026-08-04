from pathlib import Path

import numpy as np

from opencae.model.entities.optimization import (
    FilterRadius,
    TopologyFilterSettings,
    TopologySymmetry,
)
from opencae.optimization.filtering import build_filter_operators
from opencae.optimization.oc import optimality_criteria_update
from opencae.optimization.res_reader import ResFieldReader, dense_values


def test_res_reader_reads_dense_topology_fields_by_solver_id(tmp_path: Path):
    path = tmp_path / "model.res"
    path.write_text(
        """LC 1
FIELD, NAME=DENS_GRAD, TYPE=ELEMENT, COLS=1, ROWS=4
0.0
-1.0
-2.0
-3.0
END FIELD
FIELD, NAME=VOLUME, TYPE=ELEMENT, COLS=1, ROWS=4
0.0
10.0
11.0
12.0
END FIELD
""",
        encoding="utf-8",
    )
    fields = ResFieldReader().read_fields(path, names={"DENS_GRAD", "VOLUME"})
    ids = np.asarray([1, 3], dtype=np.int64)
    assert np.allclose(dense_values(fields["DENS_GRAD"], ids)[:, 0], [-1.0, -3.0])
    assert np.allclose(dense_values(fields["VOLUME"], ids)[:, 0], [10.0, 12.0])


def test_two_filter_radii_are_resolved_independently():
    points = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    settings = TopologyFilterSettings(
        name="Filter",
        density_constraint_radius=FilterRadius(True, 2.5, 0.0),
        sensitivity_radius=FilterRadius(True, 5.0, 0.0),
    )
    operators = build_filter_operators(points, settings)
    assert operators.minimum_distance == 1.0
    assert operators.density_constraint_radius == 2.5
    assert operators.sensitivity_radius == 5.0
    assert operators.sensitivity.nnz >= operators.density_constraint.nnz


def test_manual_density_radius_can_be_smaller_than_element_spacing():
    points = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    settings = TopologyFilterSettings(
        name="Filter",
        density_constraint_radius=FilterRadius(False, 2.5, 0.25),
        sensitivity_radius=FilterRadius(False, 5.0, 2.0),
    )
    operators = build_filter_operators(points, settings)
    assert operators.density_constraint_radius == 0.25
    assert operators.sensitivity_radius == 2.0


def test_filter_does_not_couple_non_design_elements():
    points = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    settings = TopologyFilterSettings(name="Filter")
    operators = build_filter_operators(
        points,
        settings,
        active_mask=np.asarray([True, True, False]),
    )
    physical = operators.physical_density(np.asarray([0.2, 0.8, 1.0]))
    assert physical[2] == 1.0
    assert physical[0] < 1.0
    assert physical[1] < 1.0


def test_planar_symmetry_density_matrix_equalizes_mirrored_points():
    points = np.asarray([[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    symmetry = TopologySymmetry(
        name="Mirror",
        reference={"kind": "datum_plane", "origin": (0, 0, 0), "normal": (1, 0, 0)},
    )
    settings = TopologyFilterSettings(
        name="Filter",
        density_constraint_radius=FilterRadius(False, 1.0, 0.25),
        sensitivity_radius=FilterRadius(False, 1.0, 1.0),
    )
    operators = build_filter_operators(points, settings, [symmetry])
    physical = operators.physical_density(np.asarray([0.2, 0.8]))
    assert np.allclose(physical, [0.5, 0.5])


def test_oc_bisection_meets_volume_fraction_constraint():
    density = np.full(4, 0.5)
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
        constraint_limit=0.4,
        evaluate_constraint=lambda value: float(np.mean(value)),
        tolerance=1.0e-10,
        maximum_steps=200,
    )
    assert float(np.mean(result.density)) <= 0.400001
    assert np.all(result.density >= 1.0e-3)
    assert np.all(result.density <= 1.0)


def test_topology_model_roundtrip_preserves_separate_radii():
    from opencae.model.core import decode_model, encode_model
    from opencae.model.entities.optimization import TopologyOptimization
    from opencae.model.entities.project import Project

    optimization = TopologyOptimization(name="Topology-1")
    optimization.filter_settings.density_constraint_radius.factor = 2.25
    optimization.filter_settings.sensitivity_radius.factor = 5.5
    decoded = decode_model(encode_model(Project(name="P", optimizations=[optimization])))
    restored = decoded.optimizations[0].filter_settings
    assert restored.density_constraint_radius.factor == 2.25
    assert restored.sensitivity_radius.factor == 5.5


def test_topology_deck_uses_native_femaster_topology_loadcase(project_factory):
    from opencae.model.core import EntityRef
    from opencae.model.entities.optimization import (
        OptimizationConstraint,
        OptimizationObjective,
        OptimizationResponse,
        ResponseType,
        TopologyOptimization,
    )
    from opencae.optimization import build_mesh_index, render_topology_deck

    data = project_factory(two_instances=True, include_constraints=False)
    project = data["project"]
    stiffness = OptimizationResponse(name="Compliance", response_type=ResponseType.STIFFNESS_ENERGY)
    volume = OptimizationResponse(name="Volume Fraction", response_type=ResponseType.VOLUME_FRACTION)
    optimization = TopologyOptimization(
        name="Topology-1",
        analysis_ref=EntityRef.of(data["analysis"], "Analysis"),
        responses=[stiffness, volume],
        objectives=[OptimizationObjective(name="Minimize", response_ref=EntityRef.of(stiffness, "OptimizationResponse"))],
        constraints=[OptimizationConstraint(name="Volume", response_ref=EntityRef.of(volume, "OptimizationResponse"), limit=0.5)],
    )
    project.optimizations.append(optimization)
    project.rebuild_index()
    index = build_mesh_index(project)
    deck = render_topology_deck(project, optimization, index, np.full(index.count, 0.5))
    assert "*LOADCASE, TYPE=LINEARSTATICTOPO" in deck
    assert "*TOPODENSITY, FIELD=OPENCAE_TOPO_DENSITY" in deck
    assert "*TOPOEXPONENT" in deck
    assert "*FIELD, NAME=OPENCAE_TOPO_DENSITY, TYPE=ELEMENT, COLS=1" in deck
    assert "*END" not in deck
