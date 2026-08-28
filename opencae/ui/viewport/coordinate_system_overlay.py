"""Coordinate persistent coordinate-system visuals with the active camera."""

from __future__ import annotations

import numpy as np

from .coordinate_system_visual import (
    CoordinateSystemVisual,
    ring_geometry as _ring_geometry,
)
from .instance_transform import transform_points, transform_vector
from .screen_scale import world_size_for_pixels


class CoordinateSystemOverlay:
    """Own visible coordinate systems and update their existing actor transforms."""

    def __init__(self):
        self._visuals: list[CoordinateSystemVisual] = []
        self._camera = None
        self._observer_id = None

    def clear(self, plotter):
        """Remove all persistent visuals while retaining the camera observer."""
        for visual in self._visuals:
            visual.clear(plotter)
        self._visuals.clear()

    def show_part(self, plotter, part, scene=None):
        """Replace the overlay with visible systems owned by one Part."""
        self._observe_camera(plotter)
        records = [
            (system, f"part-{index}", None)
            for index, system in enumerate(getattr(part, "coordinate_systems", ()))
            if _visible(scene, system)
        ]
        self._replace_records(plotter, records)

    def show_assembly(self, plotter, project, scene):
        """Replace the overlay with Assembly and transformed Part systems."""
        self._observe_camera(plotter)
        records = [
            (system, f"assembly-{index}", None)
            for index, system in enumerate(project.assembly.coordinate_systems)
            if _visible(scene, system)
        ]
        for instance_id, instance in scene.assembly_instances.items():
            part = project.try_resolve(instance.part_ref)
            if part is None:
                continue
            records.extend(
                (system, f"{instance_id}-{index}", instance)
                for index, system in enumerate(part.coordinate_systems)
                if _visible(scene, system)
            )
        self._replace_records(plotter, records)

    def _replace_records(self, plotter, records):
        """Recreate visuals only when the displayed model context changes."""
        self.clear(plotter)
        for system, key, instance in records:
            origin = np.asarray(system.origin, dtype=float)
            axes = self._axes(system)
            if instance is not None:
                origin = transform_points([origin], instance)[0]
                axes = tuple(transform_vector(axis, instance) for axis in axes)
            cylindrical = str(system.system_type).lower().startswith("cyl")
            labels = ("r", "θ", "z") if cylindrical else ("x", "y", "z")
            visual = CoordinateSystemVisual(
                plotter,
                key=key,
                name=system.name,
                origin=origin,
                axes=axes,
                labels=labels,
                cylindrical=cylindrical,
            )
            visual.set_scale(world_size_for_pixels(plotter, origin, 44))
            self._visuals.append(visual)

    def _observe_camera(self, plotter):
        camera = getattr(plotter, "camera", None)
        if camera is None or camera is self._camera:
            return
        if self._camera is not None and self._observer_id is not None:
            try:
                self._camera.RemoveObserver(self._observer_id)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass
        self._camera = camera
        self._observer_id = None
        try:
            self._observer_id = camera.AddObserver(
                "ModifiedEvent",
                lambda *_args: self.refresh_scale(plotter),
            )
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self._observer_id = None

    def refresh_scale(self, plotter):
        """Update actor transforms and label points without rebuilding pipelines."""
        if not self._visuals:
            return False
        for visual in self._visuals:
            visual.set_scale(
                world_size_for_pixels(plotter, visual.origin, 44)
            )
        return True

    @staticmethod
    def _axes(system):
        x = CoordinateSystemOverlay._unit(system.axis_1)
        y0 = np.asarray(system.axis_2, dtype=float)
        y = CoordinateSystemOverlay._unit(y0 - np.dot(y0, x) * x)
        z = CoordinateSystemOverlay._unit(np.cross(x, y))
        if str(system.system_type).lower().startswith("cyl"):
            z, x = x, y
            y = CoordinateSystemOverlay._unit(np.cross(z, x))
        return x, y, z

    @staticmethod
    def _unit(value):
        vector = np.asarray(value, dtype=float)
        norm = np.linalg.norm(vector)
        return vector / norm if norm > 1e-14 else np.asarray((1.0, 0.0, 0.0))


def _visible(scene, entity):
    visibility = getattr(getattr(scene, "owner", None), "visibility", None)
    return visibility is None or visibility.is_entity_visible(entity)
