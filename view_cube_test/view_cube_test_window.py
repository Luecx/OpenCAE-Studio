"""Own the standalone window used to verify live ViewCube orientation."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QMouseEvent, QPainter
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from opencae.ui.core.theme import PALETTE
from opencae.ui.viewport.view_cube import ViewCube
from opencae.ui.viewport.view_cube_polyhedron import Point3D, view_rotation


class ViewCubeTestWindow(QWidget):
    """Provide a draggable viewport-like surface that drives the ViewCube live."""

    def __init__(self) -> None:
        """Create the isolated rotation surface and status display."""
        super().__init__()
        self.setWindowTitle("OpenCAE beveled ViewCube test")
        self.resize(760, 500)
        self.setMinimumSize(520, 360)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._drag_position: QPointF | None = None
        self._yaw, self._pitch = -35.0, 25.0
        self.cube = ViewCube(self)
        self.cube.set_view_matrix(view_rotation(self._yaw, self._pitch))
        self.status = QLabel("Drag the viewport — the ViewCube must follow live", self)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(
            f"color: {PALETTE['text']}; background: {PALETTE['panel']}; "
            f"border: 1px solid {PALETTE['border_light']}; border-radius: 6px; "
            "padding: 8px 12px;"
        )
        self.status.setMinimumWidth(430)
        self.cube.view_requested.connect(self._show_direction)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addStretch(1)
        layout.addWidget(self.status, 0, Qt.AlignmentFlag.AlignHCenter)

    def paintEvent(self, event) -> None:
        """Paint a deterministic viewport grid without relying on OpenGL."""
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PALETTE["viewport"]))
        painter.setPen(QColor(PALETTE["border"]))
        for x in range(0, self.width(), 36):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 36):
            painter.drawLine(0, y, self.width(), y)
        painter.end()

    def resizeEvent(self, event) -> None:
        """Keep the cube anchored to the viewport's upper-right corner."""
        super().resizeEvent(event)
        self.cube.move(self.width() - self.cube.width() - 18, 18)
        self.cube.raise_()
        self.status.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin a camera-orbit gesture on a left-button viewport press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Mirror a viewport orbit into the ViewCube orientation in real time."""
        if self._drag_position is None:
            return
        delta = event.position() - self._drag_position
        self._drag_position = event.position()
        self._yaw = (self._yaw + delta.x() * 0.55) % 360.0
        self._pitch = max(-89.0, min(89.0, self._pitch - delta.y() * 0.55))
        self.cube.set_view_matrix(view_rotation(self._yaw, self._pitch))
        self.status.setText(f"Camera: yaw {self._yaw:.1f}°, pitch {self._pitch:.1f}°")

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish an active viewport-orbit gesture."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            self.unsetCursor()

    def _show_direction(self, normal: Point3D) -> None:
        """Show the orthogonal or diagonal direction represented by a face click."""
        values = ", ".join(f"{value:+.2f}" for value in normal)
        self.status.setText(f"Requested world-space normal: ({values})")
