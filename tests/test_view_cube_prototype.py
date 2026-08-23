"""Regression coverage for the production camera-oriented ViewCube."""

from __future__ import annotations

import os
from collections import Counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget

from opencae.ui.viewport.view_cube import ViewCube
from opencae.ui.viewport.view_cube_camera import ViewCubeCameraController
from opencae.ui.viewport.view_cube_polyhedron import (
    beveled_cube_faces,
    camera_view_matrix,
    view_rotation,
)
from opencae.ui.viewport.viewport_canvas import ViewportCanvas

_QT_APPLICATION: QApplication | None = None


def _application() -> QApplication:
    """Return the single Qt application required for offscreen widget tests."""
    global _QT_APPLICATION
    _QT_APPLICATION = QApplication.instance() or QApplication([])
    return _QT_APPLICATION


def _render(widget: ViewCube) -> QImage:
    """Render the production cube into a transparent-initialized target."""
    image = QImage(widget.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    widget.render(image)
    return image


def test_beveled_cube_has_expected_face_topology() -> None:
    """Keep six main, twelve edge, and eight corner surfaces explicit."""
    faces = beveled_cube_faces()
    assert sum(face[0] == "main" for face in faces) == 6
    assert sum(face[0] == "edge" for face in faces) == 12
    assert sum(face[0] == "corner" for face in faces) == 8


def test_beveled_cube_is_a_closed_manifold_with_twenty_four_vertices() -> None:
    """Reject overlapping faces or triangles connected to unrelated coordinates."""
    faces = beveled_cube_faces()
    vertices = {point for face in faces for point in face[3]}
    edges = Counter()
    vertex_faces = Counter()
    for _kind, _label, _normal, polygon in faces:
        for point in polygon:
            vertex_faces[point] += 1
        for index, point in enumerate(polygon):
            edge = tuple(sorted((point, polygon[(index + 1) % len(polygon)])))
            edges[edge] += 1

    assert len(vertices) == 24
    assert set(vertex_faces.values()) == {4}
    assert len(edges) == 48
    assert set(edges.values()) == {2}


def test_face_shapes_match_square_rectangle_triangle_contract() -> None:
    """Keep main faces square and connector faces narrow rather than octagonal."""
    faces = beveled_cube_faces()

    assert {len(face[3]) for face in faces if face[0] == "main"} == {4}
    assert {len(face[3]) for face in faces if face[0] == "edge"} == {4}
    assert {len(face[3]) for face in faces if face[0] == "corner"} == {3}


def test_generic_orientation_keeps_all_visible_connector_faces() -> None:
    """Prevent shallow but front-facing edge strips from disappearing during orbit."""
    _application()
    widget = ViewCube()
    widget.set_view_matrix(view_rotation(52.0, -31.0, 14.0))
    visible = widget._visible_faces()

    assert sum(face[1][0] == "main" for face in visible) == 3
    assert sum(face[1][0] == "edge" for face in visible) == 6
    assert sum(face[1][0] == "corner" for face in visible) == 4


def test_view_cube_paints_opaque_non_uniform_pixels() -> None:
    """Ensure a complete raster is produced instead of a transparent black box."""
    _application()
    widget = ViewCube()
    image = _render(widget)
    colors = {
        image.pixelColor(x, y).name(QColor.NameFormat.HexArgb)
        for x, y in ((0, 0), (87, 42), (57, 87), (116, 87), (87, 116))
    }
    assert len(colors) >= 4
    assert all(
        image.pixelColor(x, y).alpha() == 255
        for x in range(image.width())
        for y in range(image.height())
    )


def test_orientation_change_produces_a_different_projection() -> None:
    """Verify that external camera changes alter the displayed cube live."""
    _application()
    widget = ViewCube()
    initial = _render(widget)
    matrix = view_rotation(52.0, -31.0, 14.0)
    widget.set_view_matrix(matrix)
    rotated = _render(widget)
    assert initial != rotated
    assert widget.view_matrix == matrix


def test_view_cube_has_no_translucent_widget_surface() -> None:
    """Protect the fast opaque composition policy above the viewport widget."""
    _application()
    widget = ViewCube()
    assert widget.testAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
    assert not widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert widget.mask().isEmpty()


def test_visible_main_face_emits_world_normal() -> None:
    """Keep painted face hits connected to their world-space view normals."""
    application = _application()
    widget = ViewCube()
    emitted = []
    widget.view_requested.connect(emitted.append)
    widget.show()
    application.processEvents()
    _render(widget)
    polygon, expected, _label = next(
        region for region in reversed(widget._hit_regions) if region[2] == "TOP"
    )
    QTest.mouseClick(
        widget,
        Qt.MouseButton.LeftButton,
        pos=polygon.boundingRect().center().toPoint(),
    )
    assert emitted == [expected]


def test_camera_basis_maps_conventional_cae_views() -> None:
    """Keep top, front, and right normals aligned with existing viewport views."""
    top = camera_view_matrix((0, 0, 1), (0, 0, 0), (0, 1, 0))
    front = camera_view_matrix((0, -1, 0), (0, 0, 0), (0, 0, 1))
    right = camera_view_matrix((1, 0, 0), (0, 0, 0), (0, 0, 1))

    assert top[2] == (0.0, 0.0, 1.0)
    assert front[2] == (0.0, -1.0, 0.0)
    assert right[2] == (1.0, 0.0, 0.0)


class _Camera:
    """Minimal observable camera used to verify the production binding."""

    def __init__(self):
        self.position = (1.0, 1.0, 1.0)
        self.focal_point = (0.0, 0.0, 0.0)
        self.up = (0.0, 0.0, 1.0)
        self.callback = None

    def AddObserver(self, _event, callback):
        """Store the camera callback and return a deterministic observer id."""
        self.callback = callback
        return 17

    def RemoveObserver(self, observer_id):
        """Record successful observer removal."""
        assert observer_id == 17
        self.callback = None


class _Plotter:
    """Minimal plotter recording camera direction application side effects."""

    def __init__(self):
        self.camera = _Camera()
        self.clipping_resets = 0
        self.renders = 0

    def reset_camera_clipping_range(self):
        """Record clipping-range synchronization."""
        self.clipping_resets += 1

    def render(self):
        """Record the one requested viewport frame."""
        self.renders += 1


def test_camera_controller_tracks_and_applies_face_normals() -> None:
    """Synchronize free rotation and preserve distance on a clicked cube face."""
    _application()
    cube = ViewCube()
    plotter = _Plotter()
    controller = ViewCubeCameraController(plotter, cube)

    plotter.camera.position = (4.0, 0.0, 0.0)
    plotter.camera.up = (0.0, 0.0, 1.0)
    plotter.camera.callback()
    assert cube.view_matrix[2] == (1.0, 0.0, 0.0)

    controller.set_direction((0.0, -1.0, 0.0))
    assert plotter.camera.position == (0.0, -4.0, 0.0)
    assert plotter.clipping_resets == 1
    assert plotter.renders == 1
    controller.close()
    assert plotter.camera.callback is None


def test_canvas_reparents_opaque_cube_to_render_surface() -> None:
    """Keep the opaque cube inside the VTK surface instead of beside it."""
    application = _application()
    canvas = ViewportCanvas()
    render_surface = QWidget(canvas)

    canvas.set_render_widget(render_surface)
    canvas.resize(640, 420)
    application.processEvents()

    assert canvas.cube.parentWidget() is render_surface
    assert canvas.cube.testAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
    assert not canvas.cube.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
