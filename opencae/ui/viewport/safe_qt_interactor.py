"""Provide the Qt/PyVista interactor plus OpenCAE-owned camera navigation."""

from __future__ import annotations

from math import exp, radians, sqrt, tan

from PyQt6.QtCore import QEvent, QObject, Qt
from pyvistaqt import QtInteractor

from opencae.ui.core.theme import (
    PALETTE,
    VIEWPORT_FONT_FAMILY,
    VIEWPORT_FONT_SIZE,
)
from opencae.ui.viewport.rotation_pivot_indicator import RotationPivotIndicator
from opencae.ui.viewport.spacenav_input import SpaceNavInput


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


def _zoom_camera(plotter, factor: float) -> bool:
    """Apply one incremental magnification while preserving projection semantics."""
    try:
        factor = float(factor)
        if not (factor > _EPSILON):
            return False
        factor = min(max(factor, 0.05), 20.0)
        camera = plotter.camera
        if bool(camera.GetParallelProjection()):
            camera.SetParallelScale(
                max(_EPSILON, float(camera.GetParallelScale()) / factor)
            )
        else:
            camera.Dolly(factor)
        plotter.reset_camera_clipping_range()
        plotter.render()
        return True
    except (AttributeError, RuntimeError, TypeError, ValueError, ZeroDivisionError):
        return False


def _roll_camera(plotter, angle_degrees: float) -> bool:
    """Roll the camera so two-finger rotation follows the physical gesture."""
    try:
        angle = float(angle_degrees)
        if abs(angle) <= _EPSILON:
            return False
        plotter.camera.Roll(-angle)
        plotter.camera.OrthogonalizeViewUp()
        plotter.reset_camera_clipping_range()
        plotter.render()
        return True
    except (AttributeError, RuntimeError, TypeError, ValueError):
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


def _normalize(vector):
    length = sqrt(sum(float(value) * float(value) for value in vector))
    if length <= _EPSILON:
        return (0.0, 0.0, 0.0)
    return tuple(float(value) / length for value in vector)


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


class SafeQtInteractor(QtInteractor):
    """QtInteractor with explicit rendering cadence and deterministic CAE navigation."""

    def __init__(self, *args, **kwargs):
        kwargs["auto_update"] = False
        super().__init__(*args, **kwargs)
        self._pan_display_position = None
        self._rotation_pivot = None

        setter = getattr(self, "setAttribute", None)
        if callable(setter):
            setter(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        grab = getattr(self, "grabGesture", None)
        if callable(grab):
            grab(Qt.GestureType.PinchGesture)

        self._spacenav = None
        if isinstance(self, QObject):
            self._spacenav = SpaceNavInput(self)
            self._spacenav.motion.connect(self._handle_spacenav_motion)

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

    def add_point_labels(self, *args, **kwargs):
        """Apply one canonical font and theme legacy label colors centrally."""
        kwargs["font_size"] = VIEWPORT_FONT_SIZE
        kwargs["font_family"] = VIEWPORT_FONT_FAMILY

        # A few older preview call sites still pass the former dark-only colors.
        # Normalize them here so temporary labels remain readable in light mode.
        if str(kwargs.get("text_color", "")).lower() in {"#f7f9fb", "#f0f3f6"}:
            kwargs["text_color"] = PALETTE["overlay_text"]
        if str(kwargs.get("shape_color", "")).lower() == "#20262d":
            kwargs["shape_color"] = PALETTE["overlay_bg"]
        return super().add_point_labels(*args, **kwargs)

    def add_text(self, *args, **kwargs):
        """Keep free-standing VTK viewport text on the canonical label size."""
        kwargs["font_size"] = VIEWPORT_FONT_SIZE
        return super().add_text(*args, **kwargs)

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

    def event(self, event):
        """Handle native trackpad and touchscreen gestures before VTK mouse fallback."""
        try:
            event_type = event.type()
        except (AttributeError, RuntimeError):
            return super().event(event)
        if event_type == QEvent.Type.NativeGesture and self._handle_native_gesture(event):
            event.accept()
            return True
        if event_type == QEvent.Type.Gesture and self._handle_touch_gesture(event):
            event.accept()
            return True
        return super().event(event)

    def wheelEvent(self, event):
        """Pan high-resolution touchpad scrolls while preserving mouse-wheel zoom."""
        try:
            pixels = event.pixelDelta()
            modifiers = event.modifiers()
            is_trackpad_scroll = not pixels.isNull()
            wants_zoom = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        except (AttributeError, RuntimeError, TypeError):
            return super().wheelEvent(event)
        if is_trackpad_scroll and not wants_zoom:
            if self._pan_pixels(float(pixels.x()), float(pixels.y())):
                event.accept()
                return
        super().wheelEvent(event)

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

    def closeEvent(self, event):
        """Release optional device input before Qt tears down the GL widget."""
        spacenav = getattr(self, "_spacenav", None)
        if spacenav is not None:
            spacenav.close()
        super().closeEvent(event)

    def _handle_native_gesture(self, event) -> bool:
        """Map Qt's OS-level trackpad gestures onto the existing CAE camera model."""
        try:
            gesture_type = event.gestureType()
        except (AttributeError, RuntimeError):
            return False
        if gesture_type == Qt.NativeGestureType.PanNativeGesture:
            delta = event.delta()
            return self._pan_pixels(float(delta.x()), float(delta.y()))
        if gesture_type == Qt.NativeGestureType.ZoomNativeGesture:
            return _zoom_camera(self, 1.0 + float(event.value()))
        if gesture_type == Qt.NativeGestureType.RotateNativeGesture:
            return _roll_camera(self, float(event.value()))
        return gesture_type in {
            Qt.NativeGestureType.BeginNativeGesture,
            Qt.NativeGestureType.EndNativeGesture,
        }

    def _handle_touch_gesture(self, event) -> bool:
        """Use one two-finger pinch stream for zoom, pan, and in-plane rotation."""
        try:
            pinch = event.gesture(Qt.GestureType.PinchGesture)
        except (AttributeError, RuntimeError):
            return False
        if pinch is None:
            return False

        handled = False
        try:
            flags = pinch.changeFlags()
            scale_flag = pinch.ChangeFlag.ScaleFactorChanged
            center_flag = pinch.ChangeFlag.CenterPointChanged
            rotation_flag = pinch.ChangeFlag.RotationAngleChanged

            if flags & scale_flag:
                previous = float(pinch.lastScaleFactor())
                current = float(pinch.scaleFactor())
                factor = current / previous if previous > _EPSILON else current
                handled = _zoom_camera(self, factor) or handled

            if flags & center_flag:
                current = pinch.centerPoint()
                previous = pinch.lastCenterPoint()
                handled = self._pan_pixels(
                    float(current.x() - previous.x()),
                    float(current.y() - previous.y()),
                ) or handled

            if flags & rotation_flag:
                angle = float(pinch.rotationAngle() - pinch.lastRotationAngle())
                handled = _roll_camera(self, angle) or handled
        except (AttributeError, RuntimeError, TypeError, ValueError, ZeroDivisionError):
            return False
        return handled

    def _pan_pixels(self, dx: float, dy: float) -> bool:
        try:
            width, height = self.GetRenderWindow().GetSize()
            center = (float(width) * 0.5, float(height) * 0.5)
            current = (center[0] + float(dx), center[1] - float(dy))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False
        return _pan_camera(self, center, current)

    def _handle_spacenav_motion(self, values) -> None:
        """Apply one libspnav 6-DoF sample in camera-local coordinates."""
        try:
            tx, ty, tz, rx, ry, rz, period = values
            tx = float(tx)
            ty = float(ty)
            tz = float(tz)
            rx = float(rx)
            ry = float(ry)
            rz = float(rz)
            period = int(period)
            camera = self.camera
            focal = tuple(float(value) for value in camera.GetFocalPoint())
            position = tuple(float(value) for value in camera.GetPosition())
            up = _normalize(tuple(float(value) for value in camera.GetViewUp()))
            forward = _normalize(tuple(focal[i] - position[i] for i in range(3)))
            right = _normalize(_cross(forward, up))
            distance = max(float(camera.GetDistance()), _EPSILON)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return

        # libspnav values are roughly in a few-hundred-count range. Scale by the
        # current camera distance so the same hand motion feels similar on tiny
        # and very large CAE models. period only dampens unusually sparse samples.
        cadence = min(max(period / 16.0, 0.5), 2.0) if period > 0 else 1.0
        translation_scale = distance * 0.00010 * cadence
        offset = tuple(
            translation_scale * (right[i] * tx + up[i] * ty)
            for i in range(3)
        )
        camera.SetPosition(*(position[i] + offset[i] for i in range(3)))
        camera.SetFocalPoint(*(focal[i] + offset[i] for i in range(3)))

        if abs(tz) > _EPSILON:
            factor = exp(max(min(tz * 0.0012 * cadence, 1.0), -1.0))
            if bool(camera.GetParallelProjection()):
                camera.SetParallelScale(
                    max(_EPSILON, float(camera.GetParallelScale()) / factor)
                )
            else:
                camera.Dolly(factor)

        rotation_scale = 0.018 * cadence
        if abs(ry) > _EPSILON:
            camera.Azimuth(ry * rotation_scale)
        if abs(rx) > _EPSILON:
            camera.Elevation(rx * rotation_scale)
        if abs(rz) > _EPSILON:
            camera.Roll(-rz * rotation_scale)
        camera.OrthogonalizeViewUp()
        try:
            self.reset_camera_clipping_range()
            self.render()
        except (AttributeError, RuntimeError):
            pass

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
