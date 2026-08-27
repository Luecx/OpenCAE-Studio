"""Bind the Qt ViewCube orientation and face requests to one VTK camera."""

from __future__ import annotations

import logging
from math import isfinite, sqrt

LOGGER = logging.getLogger(__name__)


class ViewCubeCameraController:
    """Synchronize a ViewCube with a plotter camera for its full lifetime."""

    def __init__(self, plotter, cube) -> None:
        """Install a live camera observer and initialize the cube orientation."""
        self.plotter = plotter
        self.cube = cube
        self.camera = getattr(plotter, "camera", None)
        self._observer_id = None
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
        """Move the camera onto a clicked main, edge, or corner normal."""
        direction = _normalized_direction(normal)
        if direction is None or self.camera is None:
            return
        try:
            focal = tuple(float(value) for value in self.camera.focal_point)
            position = tuple(float(value) for value in self.camera.position)
            distance = sqrt(
                sum((position[index] - focal[index]) ** 2 for index in range(3))
            )
            distance = distance if distance > 1.0e-9 else 1.0
            self.camera.position = tuple(
                focal[index] + direction[index] * distance for index in range(3)
            )
            self.camera.up = _stable_view_up(direction)
            self.plotter.reset_camera_clipping_range()
            self.plotter.render()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return
        except Exception:
            LOGGER.exception("Unexpected failure while applying a ViewCube direction")

    def close(self) -> None:
        """Remove the VTK observer before the owning viewport is destroyed."""
        if self.camera is None or self._observer_id is None:
            return
        try:
            self.camera.RemoveObserver(self._observer_id)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass
        self._observer_id = None


def _normalized_direction(value):
    """Validate and normalize an emitted world-space face normal."""
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


def _stable_view_up(direction):
    """Return conventional Z-up except for views close to the Z axis."""
    candidate = (0.0, 1.0, 0.0) if abs(direction[2]) > 0.92 else (0.0, 0.0, 1.0)
    projection = sum(candidate[index] * direction[index] for index in range(3))
    values = tuple(
        candidate[index] - projection * direction[index] for index in range(3)
    )
    length = sqrt(sum(value * value for value in values))
    return tuple(value / length for value in values)
