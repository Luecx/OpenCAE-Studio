"""Mesh Path, field history and mesh-convergence regression tests."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from opencae.model.entities.jobs import ResultSet
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.model.project import Project
from opencae.persistence.project_codec import project_from_dict, project_to_dict
from opencae.results.frd_data import FrdData, FrdFieldData
from opencae.results.mesh_convergence import assess_convergence
from opencae.results.mesh_path import (
    MeshPath, create_mesh_path, finite_series, path_field_series,
    shortest_edge_path, stored_paths, time_field_series,
)


@pytest.fixture
def graph():
    coordinates = {
        1: (0., 0., 0.), 2: (1., 0., 0.), 3: (2., 0., 0.),
        4: (1., 1., 0.), 5: (2., 1., 0.),
        9: (10., 10., 10.),
    }
    adjacent = {key: {} for key in coordinates}
    for a, b in [(1, 2), (2, 3), (2, 4), (4, 5), (5, 3)]:
        length = float(np.linalg.norm(
            np.asarray(coordinates[a]) - np.asarray(coordinates[b])
        ))
        adjacent[a][b] = length
        adjacent[b][a] = length
    return coordinates, adjacent


def test_path_uses_connected_shortest_mesh_edges(graph):
    points, adjacent = graph
    path = create_mesh_path("Beam", (1, 3), points, adjacent)
    assert path.waypoints == (1, 3)
    assert path.node_ids == (1, 2, 3)
    assert path.distances == pytest.approx((0., 1., 2.))


def test_waypoints_are_ordered_and_mandatory(graph):
    points, adjacent = graph
    path = create_mesh_path("Corner", (1, 4, 3), points, adjacent)
    assert path.node_ids[:3] == (1, 2, 4)
    assert path.node_ids[-1] == 3
    assert path.distances[-1] == pytest.approx(4.)


def test_disconnected_nodes_are_rejected(graph):
    _, adjacent = graph
    with pytest.raises(ValueError, match="No connected mesh-edge route"):
        shortest_edge_path(adjacent, 1, 9)
    with pytest.raises(ValueError, match="Unknown path node"):
        shortest_edge_path(adjacent, 1, 42)


def test_path_data_roundtrip_and_result_metadata(graph):
    coords, adjacent = graph
    path = create_mesh_path("Sample", (1, 3), coords, adjacent)
    result = ResultSet(name="My result", metadata={"mesh_paths": [path.as_dict()]})
    assert stored_paths(result) == (path,)


def test_path_y_field_and_time_y_field():
    block1 = FrdFieldData(
        name="DISP", components=["D1", "D2", "D3"],
        values={1: [1., 0., 0.], 2: [2., 0., 0.], 3: [3., 0., 0.]},
        step_id=1, frame_id=1, frame_value=0.25,
    )
    block2 = FrdFieldData(
        name="DISP", components=["D1", "D2", "D3"],
        values={1: [10., 0., 0.], 2: [20., 0., 0.], 3: [30., 0., 0.]},
        step_id=1, frame_id=2, frame_value=0.75,
    )
    data = FrdData(nodes={i: (float(i), 0., 0.) for i in (1, 2, 3)},
                   fields=[block1, block2])
    loader = SimpleNamespace(read=lambda _: data)
    path = MeshPath("line", (1, 3), (1, 2, 3), (0., 1., 2.))
    x, y = path_field_series(loader, "unused.frd", path, "DISP", "D1", 1, 1)
    assert x == (0., 1., 2.)
    assert y == (1., 2., 3.)
    x, y = path_field_series(
        loader, "unused.frd", path, "DISP", "Magnitude", 1, 2, "node_id"
    )
    assert x == (1., 2., 3.)
    assert y == (10., 20., 30.)
    x, y = time_field_series(loader, "unused.frd", 2, "DISP", "D1", 1)
    assert x == (.25, .75)
    assert y == (2., 20.)


def test_missing_fields_are_masked_in_paired_series():
    assert finite_series((0., 1., 2.), (3., np.nan, 5.)) == (
        (0., 2.), (3., 5.)
    )


def test_study_persistence_roundtrip_and_metric_settings():
    project = Project(name="Test")
    study = MeshConvergenceStudy(
        name="Refinement",
        mesh_scales=[1.0, .7, .5, .35],
        field_name="STRESS",
        component="Mises",
        metric="weighted_p95",
        exclude_radius=.2,
        relative_tolerance=.01,
    )
    project.studies.append(study)
    project.rebuild_index(strict=True)
    recovered = project_from_dict(project_to_dict(project))
    item = recovered.studies[0]
    assert isinstance(item, MeshConvergenceStudy)
    assert item.field_name == "STRESS"
    assert item.component == "Mises"
    assert item.mesh_scales == [1., .7, .5, .35]
    assert item.exclude_radius == .2


def test_two_terminal_refinements_are_needed():
    samples = [
        {"elements": 100, "value": 10.0},
        {"elements": 300, "value": 10.2},
        {"elements": 800, "value": 10.24},
        {"elements": 1800, "value": 10.25},
    ]
    assert "within tolerance" in assess_convergence(samples, .01, "probe")
    assert "Diagnostic only" in assess_convergence(samples, .01, "nodal_max")
    assert "Not converged" in assess_convergence(samples, .001, "probe")
    assert "increase strictly" in assess_convergence(
        samples[:2] + [{"elements": 200, "value": 10.23}], .01, "probe"
    )
