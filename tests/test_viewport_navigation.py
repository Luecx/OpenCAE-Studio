"""Regression tests for camera pan and perspective/parallel projection behavior."""

from __future__ import annotations

from math import isclose, radians, tan
from pathlib import Path

from opencae.ui.viewport.safe_qt_interactor import (
    _pan_camera,
    _set_parallel_projection,
)


ROOT = Path(__file__).resolve().parents[1]


class _Camera:
    def __init__(self):
        self.position = (1.0, 2.0, 10.0)
        self.focal = (1.0, 2.0, 0.0)
        self.parallel = 0
        self.parallel_scale = 1.0
        self.view_angle = 30.0

    def GetPosition(self):
        return self.position

    def SetPosition(self, *value):
        self.position = tuple(value)

    def GetFocalPoint(self):
        return self.focal

    def SetFocalPoint(self, *value):
        self.focal = tuple(value)

    def GetDistance(self):
        return sum(
            (self.position[i] - self.focal[i]) ** 2 for i in range(3)
        ) ** 0.5

    def GetParallelProjection(self):
        return self.parallel

    def SetParallelProjection(self, value):
        self.parallel = int(value)

    def GetParallelScale(self):
        return self.parallel_scale

    def SetParallelScale(self, value):
        self.parallel_scale = float(value)

    def GetViewAngle(self):
        return self.view_angle


class _Renderer:
    """Identity display/world projection sufficient to verify translation invariants."""

    def __init__(self):
        self.display = (0.0, 0.0, 0.0)
        self.world = (0.0, 0.0, 0.0, 1.0)

    def SetWorldPoint(self, x, y, z, w):
        self.world = (x, y, z, w)

    def WorldToDisplay(self):
        self.display = self.world[:3]

    def GetDisplayPoint(self):
        return self.display

    def SetDisplayPoint(self, x, y, z):
        self.display = (x, y, z)

    def DisplayToWorld(self):
        self.world = (*self.display, 1.0)

    def GetWorldPoint(self):
        return self.world


class _Plotter:
    def __init__(self):
        self.camera = _Camera()
        self.renderer = _Renderer()
        self.render_count = 0
        self.clip_count = 0

    def render(self):
        self.render_count += 1

    def reset_camera_clipping_range(self):
        self.clip_count += 1


def test_middle_drag_pan_preserves_camera_direction_and_translates_focal_point():
    plotter = _Plotter()
    before_direction = tuple(
        plotter.camera.position[i] - plotter.camera.focal[i] for i in range(3)
    )

    assert _pan_camera(plotter, (10.0, 20.0), (14.0, 17.0))

    after_direction = tuple(
        plotter.camera.position[i] - plotter.camera.focal[i] for i in range(3)
    )
    assert after_direction == before_direction
    assert plotter.camera.focal == (-3.0, 5.0, 0.0)
    assert plotter.camera.position == (-3.0, 5.0, 10.0)
    assert plotter.render_count == 1
    assert plotter.clip_count == 1


def test_projection_toggle_preserves_apparent_scale_in_both_directions():
    plotter = _Plotter()
    expected_scale = plotter.camera.GetDistance() * tan(radians(15.0))

    assert _set_parallel_projection(plotter, True)
    assert plotter.camera.parallel == 1
    assert isclose(plotter.camera.parallel_scale, expected_scale)

    plotter.camera.parallel_scale *= 0.5
    assert _set_parallel_projection(plotter, False)
    assert plotter.camera.parallel == 0
    assert isclose(plotter.camera.GetDistance(), 5.0)


def test_rotation_pivot_is_rendered_inside_vtk_not_as_qt_child_overlay():
    pivot = (ROOT / "opencae/ui/viewport/rotation_pivot_indicator.py").read_text(
        encoding="utf-8"
    )
    interactor = (ROOT / "opencae/ui/viewport/safe_qt_interactor.py").read_text(
        encoding="utf-8"
    )
    canvas = (ROOT / "opencae/ui/viewport/viewport_canvas.py").read_text(
        encoding="utf-8"
    )

    assert "vtkActor2D" in pivot
    assert "vtkRegularPolygonSource" in pivot
    assert "renderer.add_actor" in pivot
    assert "AddActor2D" not in pivot
    assert "QWidget" not in pivot
    assert "self._rotation_pivot = None" in interactor
    assert "RotationPivotIndicator(renderer)" in interactor
    assert "_ensure_rotation_pivot" in interactor
    assert "rotation_pivot" not in canvas
