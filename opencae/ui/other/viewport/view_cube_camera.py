"""Bind the Qt ViewCube orientation and face requests to one VTK camera."""

from __future__ import annotations

import logging
from math import acos, cos, isfinite, pi, sin, sqrt

from PyQt6.QtCore import QEasingCurve, QVariantAnimation

LOGGER = logging.getLogger(__name__)


class ViewCubeCameraController:
    """Synchronize a ViewCube with a plotter camera for its full lifetime."""

    def __init__(self, plotter, cube) -> None:
        """Install a live camera observer and initialize the cube orientation."""
        self.plotter = plotter
        self.cube = cube
        self.camera = getattr(plotter, "camera", None)
        self._observer_id = None
        self._transition = None
        self._animation = QVariantAnimation()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(220)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.valueChanged.connect(self._apply_transition)
        self._animation.finished.connect(self._finish_transition)
        if self.camera is not None:
            try:
                self._observer_id = self.camera.AddObserver(
                    "ModifiedEvent",
                    self.sync,
                )
            except (AttributeError, RuntimeError, TypeError, ValueError):
                self._observer_id = None
        self.sync()

    def sync(self, *_args) -> None:
        """Copy the current VTK camera basis into the QPainter cube."""
        if self.camera is None:
            return
        try:
            self.cube.set_camera(
                self.camera.position,
                self.camera.focal_point,
                self.camera.up,
            )
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return
        except Exception:
            LOGGER.exception("Unexpected failure while synchronizing the ViewCube")

    def set_direction(self, normal) -> None:
        """Animate the camera onto a clicked main, edge, or corner normal."""
        direction = _normalized_direction(normal)
        if direction is None or self.camera is None:
            return
        try:
            focal = tuple(float(value) for value in self.camera.focal_point)
            position = tuple(float(value) for value in self.camera.position)
            offset = tuple(position[index] - focal[index] for index in range(3))
            distance = sqrt(sum(value * value for value in offset))
            distance = distance if distance > 1.0e-9 else 1.0
            start_direction = _normalized_direction(offset) or direction
            start_up = _normalized_direction(self.camera.up) or _stable_view_up(start_direction)
            target_up = _stable_view_up(direction)
            self._transition = (
                start_direction,
                direction,
                focal,
                distance,
                start_up,
                target_up,
            )
            self._animation.stop()
            self._animation.setCurrentTime(0)
            self._animation.start()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return
        except Exception:
            LOGGER.exception("Unexpected failure while applying a ViewCube direction")

    def _apply_transition(self, value) -> None:
        """Apply one eased spherical interpolation frame to the VTK camera."""
        if self.camera is None or self._transition is None:
            return
        try:
            alpha = min(max(float(value), 0.0), 1.0)
            start, target, focal, distance, start_up, target_up = self._transition
            direction = _slerp_direction(start, target, alpha)
            up = _interpolated_view_up(start_up, target_up, direction, alpha)
            self.camera.position = tuple(
                focal[index] + direction[index] * distance for index in range(3)
            )
            self.camera.up = up
            self.plotter.reset_camera_clipping_range()
            self.plotter.render()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self._animation.stop()
            self._transition = None
        except Exception:
            LOGGER.exception("Unexpected failure during ViewCube camera transition")
            self._animation.stop()
            self._transition = None

    def _finish_transition(self) -> None:
        """Release transition state after the animation reaches its exact target."""
        self._transition = None

    def close(self) -> None:
        """Remove the VTK observer before the owning viewport is destroyed."""
        self._animation.stop()
        self._transition = None
        if self.camera is None or self._observer_id is None:
            return
        try:
            self.camera.RemoveObserver(self._observer_id)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass
        self._observer_id = None


def _normalized_direction(value):
    """Validate and normalize an emitted world-space direction."""
    try:
        values = tuple(float(component) for component in value)
    except (TypeError, ValueError):
        return None
    if len(values) != 3 or not all(isfinite(component) for component in values):
        return None
    length = sqrt(sum(component * component for component in values))
    if length <= 1.0e-12:
        return None
    return tuple(component / length for component in values)


def _slerp_direction(first, second, alpha):
    """Interpolate two unit directions along the shortest stable camera arc."""
    dot = min(max(sum(a * b for a, b in zip(first, second)), -1.0), 1.0)
    if dot > 0.9995:
        blended = tuple(
            (1.0 - alpha) * first[index] + alpha * second[index]
            for index in range(3)
        )
        return _normalized_direction(blended) or second
    if dot < -0.9995:
        seed = (0.0, 0.0, 1.0) if abs(first[2]) < 0.9 else (0.0, 1.0, 0.0)
        tangent = _cross(first, seed)
        tangent = _normalized_direction(tangent) or _stable_view_up(first)
        angle = pi * alpha
        return tuple(
            cos(angle) * first[index] + sin(angle) * tangent[index]
            for index in range(3)
        )
    angle = acos(dot)
    denominator = sin(angle)
    left = sin((1.0 - alpha) * angle) / denominator
    right = sin(alpha * angle) / denominator
    return tuple(
        left * first[index] + right * second[index]
        for index in range(3)
    )


def _interpolated_view_up(first, second, direction, alpha):
    """Blend camera up while keeping it perpendicular to the viewing direction."""
    candidate = tuple(
        (1.0 - alpha) * first[index] + alpha * second[index]
        for index in range(3)
    )
    projection = sum(candidate[index] * direction[index] for index in range(3))
    projected = tuple(
        candidate[index] - projection * direction[index]
        for index in range(3)
    )
    return _normalized_direction(projected) or _stable_view_up(direction)


def _cross(first, second):
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _stable_view_up(direction):
    """Return conventional Z-up except for views close to the Z axis."""
    candidate = (0.0, 1.0, 0.0) if abs(direction[2]) > 0.92 else (0.0, 0.0, 1.0)
    projection = sum(candidate[index] * direction[index] for index in range(3))
    values = tuple(
        candidate[index] - projection * direction[index] for index in range(3)
    )
    length = sqrt(sum(value * value for value in values))
    return tuple(value / length for value in values)
