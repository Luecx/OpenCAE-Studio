"""Render the camera-oriented beveled ViewCube as an opaque Qt overlay."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from opencae.ui.core.theme import PALETTE
from .view_cube_polyhedron import (
    CubeFace,
    Matrix3D,
    Point3D,
    beveled_cube_faces,
    camera_view_matrix,
    transform,
)
from .viewport_overlay_metrics import VIEW_CUBE_SIZE


class ViewCube(QWidget):
    """Display and hit-test a beveled solid aligned with the VTK camera.

    The overlay owns all pointer input inside its rectangle. Mouse events must
    never propagate to the underlying QVTK widget because a propagated press
    without the matching release leaves VTK in an active camera-interaction
    state.
    """

    view_requested = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the cube with the application's initial isometric camera view."""
        super().__init__(parent)
        self._view_matrix = camera_view_matrix(
            (1.0, 1.0, 1.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
        )
        self._hovered_normal: Point3D | None = None
        self._pressed_normal: Point3D | None = None
        self._hit_regions: list[tuple[QPolygonF, Point3D, str]] = []
        self._faces = beveled_cube_faces()
        self.setFixedSize(VIEW_CUBE_SIZE, VIEW_CUBE_SIZE)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("View orientation cube")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)

    @property
    def view_matrix(self) -> Matrix3D:
        """Return the current world-to-view rotation matrix."""
        return self._view_matrix

    def set_camera(self, position, focal_point, view_up) -> None:
        """Update the cube from the live VTK camera vectors."""
        self.set_view_matrix(camera_view_matrix(position, focal_point, view_up))

    def set_view_matrix(self, matrix: Matrix3D) -> None:
        """Replace the world-to-view rotation used for the next paint."""
        normalized = tuple(tuple(float(value) for value in row) for row in matrix)
        if normalized == self._view_matrix:
            return
        self._view_matrix = normalized
        self._hovered_normal = None
        self.update()

    def paintEvent(self, event) -> None:
        """Project, depth-sort, and paint all currently visible faces."""
        del event
        visible_faces = self._visible_faces()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.fillRect(self.rect(), QColor(PALETTE["viewport"]))
        self._hit_regions = []
        for _depth, face, polygon, view_normal in visible_faces:
            self._draw_face(painter, face, polygon, view_normal)
            self._hit_regions.append((polygon, face[2], face[1]))
        painter.end()

    def mousePressEvent(self, event) -> None:
        """Capture pointer presses so QVTK cannot enter a camera-drag state."""
        self._pressed_normal = (
            self._normal_at(event.position())
            if event.button() == Qt.MouseButton.LeftButton
            else None
        )
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        """Highlight the foremost visible face while keeping input on the cube."""
        normal = self._normal_at(event.position())
        if normal != self._hovered_normal:
            self._hovered_normal = normal
            self.update()
        event.accept()

    def leaveEvent(self, event) -> None:
        """Clear face highlighting after the pointer exits the cube."""
        del event
        if self._hovered_normal is not None:
            self._hovered_normal = None
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        """Emit one face request only for a complete left click on the cube."""
        if event.button() == Qt.MouseButton.LeftButton:
            normal = self._normal_at(event.position())
            if normal is not None and normal == self._pressed_normal:
                self.view_requested.emit(normal)
        self._pressed_normal = None
        event.accept()

    def wheelEvent(self, event) -> None:
        """Keep wheel input above the cube from zooming the VTK camera below it."""
        event.accept()

    def _visible_faces(self) -> list[tuple[float, CubeFace, QPolygonF, Point3D]]:
        """Return front-facing polygons ordered from back toward the viewer."""
        center = QPointF(self.width() * 0.5, self.height() * 0.51)
        scale = min(self.width(), self.height()) * 0.315
        result = []
        for face in self._faces:
            view_normal = transform(self._view_matrix, face[2])
            if view_normal[2] <= 1.0e-9:
                continue
            view_points = tuple(transform(self._view_matrix, point) for point in face[3])
            polygon = QPolygonF(
                QPointF(center.x() + point[0] * scale, center.y() - point[1] * scale)
                for point in view_points
            )
            depth = sum(point[2] for point in view_points) / len(view_points)
            result.append((depth, face, polygon, view_normal))
        result.sort(key=lambda item: item[0])
        return result

    def _draw_face(self, painter, face, polygon, view_normal) -> None:
        """Paint one depth-shaded main, edge, or corner surface."""
        kind, label, world_normal, _vertices = face
        active = world_normal == self._hovered_normal
        base = {
            "main": QColor("#52697d"),
            "edge": QColor("#34495b"),
            "corner": QColor("#293b4b"),
        }[kind]
        light = max(
            0.0,
            -0.35 * view_normal[0] + 0.55 * view_normal[1] + 0.75 * view_normal[2],
        )
        fill = QColor(
            PALETTE["accent"] if active else base.lighter(82 + round(30 * light))
        )
        outline = QColor(PALETTE["accent_hover"] if active else "#91a5b5")
        painter.setPen(QPen(outline, 1.55 if active else 0.85))
        painter.setBrush(fill)
        painter.drawPolygon(polygon)
        if kind == "main" and self._polygon_area(polygon) >= 250.0:
            self._draw_label(painter, polygon, label)

    @staticmethod
    def _draw_label(painter: QPainter, polygon: QPolygonF, label: str) -> None:
        """Center a compact direction label on a sufficiently large main face."""
        font = QFont(painter.font())
        font.setPixelSize(9)
        font.setWeight(QFont.Weight.DemiBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.0)
        painter.setFont(font)
        painter.setPen(QColor("#f4f7fa"))
        painter.drawText(polygon.boundingRect(), Qt.AlignmentFlag.AlignCenter, label)

    def _normal_at(self, point: QPointF) -> Point3D | None:
        """Return the foremost painted face normal containing a local position."""
        for polygon, normal, _label in reversed(self._hit_regions):
            if polygon.containsPoint(point, Qt.FillRule.OddEvenFill):
                return normal
        return None

    @staticmethod
    def _polygon_area(polygon: QPolygonF) -> float:
        """Return screen area used to suppress labels on nearly edge-on faces."""
        return abs(
            sum(
                polygon[index].x() * polygon[(index + 1) % len(polygon)].y()
                - polygon[(index + 1) % len(polygon)].x() * polygon[index].y()
                for index in range(len(polygon))
            )
            * 0.5
        )
