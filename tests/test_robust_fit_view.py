"""Regression coverage for robust viewport framing of small/degenerate scenes."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from opencae.ui.other.viewport.scene_camera import _fit_bounds, _principal_frame, fit_camera


ROOT = Path(__file__).resolve().parents[1]


class _Plotter:
    def __init__(self, direction=(1.0, 1.0, 1.0), bounds=(-1, 1, -1, 1, -1, 1)):
        self.camera = SimpleNamespace(
            direction=tuple(direction),
            focal_point=(99.0, 99.0, 99.0),
        )
        self._bounds = tuple(bounds)
        self.reset_calls = []
        self.vector_calls = []
        self.clipping_resets = 0
        self.renders = 0

    def compute_bounds(self):
        return self._bounds

    def reset_camera(self, *, render, bounds):
        self.reset_calls.append((bool(render), tuple(bounds)))

    def view_vector(self, vector, *, viewup, render, bounds):
        self.vector_calls.append(
            (
                tuple(float(value) for value in vector),
                tuple(float(value) for value in viewup),
                bool(render),
                tuple(bounds),
            )
        )

    def reset_camera_clipping_range(self):
        self.clipping_resets += 1

    def render(self):
        self.renders += 1


def test_line_bounds_receive_finite_thickness_for_camera_reset():
    points = np.asarray(((0.0, 0.0, 0.0), (10.0, 0.0, 0.0)))
    bounds = _fit_bounds(_Plotter(), points)

    assert bounds[0:2] == (0.0, 10.0)
    assert bounds[2] < 0.0 < bounds[3]
    assert bounds[4] < 0.0 < bounds[5]
    assert np.isclose(bounds[3] - bounds[2], 0.4)
    assert np.isclose(bounds[5] - bounds[4], 0.4)


def test_two_node_diagonal_is_detected_as_one_dimensional():
    points = np.asarray(((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)))
    rank, primary, normal = _principal_frame(points)

    assert rank == 1
    assert normal is None
    assert np.isclose(abs(np.dot(primary, np.ones(3) / np.sqrt(3.0))), 1.0)


def test_fit_reorients_two_node_result_when_camera_is_end_on():
    points = np.asarray(((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)))
    direction = np.ones(3) / np.sqrt(3.0)
    plotter = _Plotter(direction=direction)

    assert fit_camera(plotter, points=points, render=True)

    assert len(plotter.vector_calls) == 1
    assert not plotter.reset_calls
    fitted_direction = np.asarray(plotter.vector_calls[0][0])
    line_direction = direction
    assert abs(float(np.dot(fitted_direction, line_direction))) < 0.8
    assert np.allclose(plotter.camera.focal_point, (0.5, 0.5, 0.5))
    assert plotter.clipping_resets == 1
    assert plotter.renders == 1


def test_fit_preserves_existing_side_view_for_line_result():
    points = np.asarray(((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)))
    plotter = _Plotter(direction=(1.0, -1.0, 0.0))

    assert fit_camera(plotter, points=points, render=False)

    assert len(plotter.reset_calls) == 1
    assert not plotter.vector_calls
    assert np.allclose(plotter.camera.focal_point, (0.5, 0.5, 0.5))
    assert plotter.clipping_resets == 1
    assert plotter.renders == 0


def test_fit_recenters_orbit_pivot_to_visible_bounds_center():
    plotter = _Plotter(
        direction=(0.0, 0.0, -1.0),
        bounds=(10.0, 14.0, -6.0, 2.0, 20.0, 24.0),
    )

    assert fit_camera(plotter, render=False)

    assert np.allclose(plotter.camera.focal_point, (12.0, -2.0, 22.0))
    assert plotter.clipping_resets == 1


def test_initial_fit_chooses_geometry_aware_view_even_when_current_view_is_safe():
    points = np.asarray(((0.0, 0.0, 0.0), (0.0, 5.0, 0.0)))
    plotter = _Plotter(direction=(1.0, 0.0, 0.0))

    assert fit_camera(
        plotter,
        points=points,
        reset_orientation=True,
        render=False,
    )

    assert len(plotter.vector_calls) == 1
    assert not plotter.reset_calls
    assert np.allclose(plotter.camera.focal_point, (0.0, 2.5, 0.0))


def test_manual_scene_fit_no_longer_depends_on_specific_actor_registry():
    source = (ROOT / "opencae/ui/other/viewport/scene_display.py").read_text(encoding="utf-8")
    fit_body = source.split("def fit(self, *, reset_orientation=False):", 1)[1].split(
        "def _fit_points", 1
    )[0]

    assert "fit_camera(" in fit_body
    assert "self.face_actors" not in fit_body
    assert "self.result_actor" not in fit_body
    assert "view_isometric" not in fit_body
