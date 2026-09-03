"""Provide the Qt/PyVista interactor plus OpenCAE-owned camera navigation."""

from __future__ import annotations

from math import radians, sqrt, tan

from PyQt6.QtCore import Qt
from pyvistaqt import QtInteractor

from opencae.ui.core.theme import PALETTE
from opencae.ui.viewport.rotation_pivot_indicator import RotationPivotIndicator


_EPSILON = 1.0e-12


def _display_to_world(renderer, x: float, y: float, z: float):
    """Unproject one VTK display coordinate into a finite 3D world position."""
    renderer.SetDisplayPoint(float(x), float(y), float(z))
    renderer.DisplayToWorld()
    point = renderer.GetWorldPoint()
    weight = float(point[3])
    if abs(weight) <= _EPSILON:
        return None
    return tuple(float(point[index]) / weight for index in range(3))


def _pan_camera(plotter, previous, current) -> bool:
    """Translate camera and focal point together so a middle drag is true panning."""
    try:
        camera = plotter.camera
        renderer = plotter.renderer
        focal = tuple(float(value) for value in camera.GetFocalPoint())
        position = tuple(float(value) for value in camera.GetPosition())

        renderer.SetWorldPoint(*focal, 1.0)
        renderer.WorldToDisplay()
        depth = float(renderer.GetDisplayPoint()[2])
        old_world = _display_to_world(renderer, previous[0], previous[1], depth)
        new_world = _display_to_world(renderer, current[0], current[1], depth)
        if old_world is None or new_world is None:
            return False

        translation = tuple(old_world[i] - new_world[i] for i in range(3))
        camera.SetPosition(*(position[i] + translation[i] for i in range(3)))
        camera.SetFocalPoint(*(focal[i] + translation[i] for i in range(3)))
        plotter.reset_camera_clipping_range()
        plotter.render()
        return True
    except (AttributeError, RuntimeError, TypeError, ValueError, ZeroDivisionError):
        return False


def _set_parallel_projection(plotter, enabled: bool) -> bool:
    """Switch projection while preserving the current apparent model scale."""
    try:
        camera = plotter.camera
        enabled = bool(enabled)
        if bool(camera.GetParallelProjection()) == enabled:
            return True

        half_angle = radians(float(camera.GetViewAngle())) * 0.5
        perspective_scale = tan(half_angle)
        if abs(perspective_scale) <= _EPSILON:
            return False

        if enabled:
            camera.SetParallelScale(
                max(_EPSILON, float(camera.GetDistance()) * perspective_scale)
            )
            camera.SetParallelProjection(1)
        else:
            focal = tuple(float(value) for value in camera.GetFocalPoint())
            position = tuple(float(value) for value in camera.GetPosition())
            offset = tuple(position[i] - focal[i] for i in range(3))
            distance = sqrt(sum(value * value for value in offset))
            target_distance = max(
                _EPSILON,
                float(camera.GetParallelScale()) / perspective_scale,
            )
            if distance > _EPSILON:
                scale = target_distance / distance
                camera.SetPosition(*(focal[i] + offset[i] * scale for i in range(3)))
            camera.SetParallelProjection(0)

        plotter.reset_camera_clipping_range()
        plotter.render()
        return True
    except (AttributeError, RuntimeError, TypeError, ValueError, ZeroDivisionError):
        return False


class SafeQtInteractor(QtInteractor):
    """QtInteractor with explicit rendering cadence and deterministic CAE navigation."""

    def __init__(self, *args, **kwargs):
        kwargs["auto_update"] = False
        super().__init__(*args, **kwargs)
        self._pan_display_position = None
        self._rotation_pivot = None

    def clear(self, *args, **kwargs):
        """Clear scene props and invalidate transient VTK navigation overlays."""
        result = super().clear(*args, **kwargs)
        # Plotter.clear() removes vtkActor2D props as well as 3D scene actors.
        # Keeping the old Python object would leave the orbit marker detached
        # from the renderer, which is why it disappeared after opening Results.
        self._rotation_pivot = None
        return result

    def add_axes(self, *args, **kwargs):
        """Create the orientation axes with the active viewport text color."""
        kwargs["color"] = PALETTE["axes"]
        return super().add_axes(*args, **kwargs)

    def refresh_theme(self) -> None:
        """Refresh transient VTK navigation and orientation colors."""
        pivot = self._rotation_pivot
        if pivot is not None:
            pivot.refresh_theme()
        try:
            self.add_axes()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def set_parallel_projection(self, enabled: bool) -> bool:
        """Toggle perspective/parallel camera projection without a visible scale jump."""
        return _set_parallel_projection(self, enabled)

    def mousePressEvent(self, event):
        """Reserve middle drag for true camera panning and expose the orbit pivot."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_display_position = self._display_position(event)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_rotation_pivot()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Pan without changing view direction; otherwise defer to VTK trackball rotation."""
        if (
            self._pan_display_position is not None
            and event.buttons() & Qt.MouseButton.MiddleButton
        ):
            current = self._display_position(event)
            if current is not None:
                _pan_camera(self, self._pan_display_position, current)
                self._pan_display_position = current
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """End custom pan/orbit feedback while preserving all other VTK input handling."""
        if (
            event.button() == Qt.MouseButton.MiddleButton
            and self._pan_display_position is not None
        ):
            self._pan_display_position = None
            event.accept()
            return
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._hide_rotation_pivot()

    def leaveEvent(self, event):
        """Drop transient navigation state when a drag exits the render surface."""
        self._pan_display_position = None
        self._hide_rotation_pivot()
        super().leaveEvent(event)

    def _display_position(self, event):
        """Convert a Qt logical-pixel event position into VTK display coordinates."""
        try:
            position = event.position()
            widget_width = max(1.0, float(self.width()))
            widget_height = max(1.0, float(self.height()))
            render_width, render_height = self.GetRenderWindow().GetSize()
            render_width = max(1.0, float(render_width))
            render_height = max(1.0, float(render_height))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None

        return (
            float(position.x()) * render_width / widget_width,
            (widget_height - 1.0 - float(position.y()))
            * render_height
            / widget_height,
        )

    def _ensure_rotation_pivot(self):
        """Create the VTK overlay only once the real PyVista renderer exists."""
        if self._rotation_pivot is not None:
            return self._rotation_pivot
        renderer = getattr(self, "renderer", None)
        if renderer is None:
            return None
        self._rotation_pivot = RotationPivotIndicator(renderer)
        return self._rotation_pivot

    def _show_rotation_pivot(self) -> None:
        """Project the camera focal point and render its marker in the VTK overlay."""
        pivot = self._ensure_rotation_pivot()
        if pivot is None:
            return
        try:
            focal = tuple(float(value) for value in self.camera.GetFocalPoint())
            self.renderer.SetWorldPoint(*focal, 1.0)
            self.renderer.WorldToDisplay()
            display_x, display_y, _ = self.renderer.GetDisplayPoint()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return
        pivot.set_center(display_x, display_y)
        pivot.show()
        self.render()

    def _hide_rotation_pivot(self) -> None:
        """Hide transient orbit feedback when no left-button rotation is active."""
        pivot = self._rotation_pivot
        if pivot is None or not pivot.is_visible():
            return
        pivot.hide()
        self.render()
