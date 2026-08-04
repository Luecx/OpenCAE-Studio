from __future__ import annotations

import numpy as np
import pyvista as pv

from .boundary_geometry import region_samples
from .screen_scale import world_size_for_pixels
from .safe_operations import remove_actor


class OrientationOverlay:
    """Draw one compact material-orientation triad per Part orientation."""

    def __init__(self):
        self._names = []

    def clear(self, plotter):
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()

    def show_part(self, plotter, project, part, scene):
        self.clear(plotter)
        for index, orientation in enumerate(getattr(part, "orientations", ())):
            if not _visible(scene, orientation):
                continue
            region = project.try_resolve(orientation.region_ref)
            if region is None:
                continue
            samples = region_samples(
                project,
                region.definition,
                scene,
                maximum=32,
            )
            if not samples:
                continue
            center = np.mean(
                np.asarray([point for point, _normal in samples], dtype=float),
                axis=0,
            )
            system = (
                project.try_resolve(orientation.coordinate_system_ref)
                if orientation.coordinate_system_ref else None
            )
            axes = _axes(system)
            self._draw(plotter, center, axes, orientation, index)

    def _draw(self, plotter, origin, axes, orientation, index):
        scale = world_size_for_pixels(plotter, origin, 42)
        colors = ("#ef6666", "#70d184", "#6ca6ff")
        labels = ("1", "2", "3")
        prefix = f"orientation-{orientation.id or index}"
        for suffix, axis, color, label in zip(labels, axes, colors, labels):
            name = f"{prefix}-{suffix}"
            self._names.append(name)
            plotter.add_mesh(
                pv.Arrow(start=origin, direction=axis, scale=scale),
                color=color,
                lighting=False,
                pickable=False,
                name=name,
                render=False,
            )
            label_name = f"{name}-label"
            self._names.append(label_name)
            plotter.add_point_labels(
                np.asarray([origin + axis * scale]),
                [label],
                name=label_name,
                show_points=False,
                point_size=0,
                font_size=9,
                text_color=color,
                shape_opacity=0,
                always_visible=False,
                render=False,
            )
        name = f"{prefix}-label"
        self._names.append(name)
        plotter.add_point_labels(
            np.asarray([origin]),
            [orientation.name],
            name=name,
            show_points=False,
            point_size=0,
            font_size=10,
            text_color="#f0f3f6",
            shape_color="#20262d",
            shape_opacity=.82,
            always_visible=False,
            render=False,
        )


def _axes(system):
    if system is None:
        return np.eye(3)
    first = _unit(system.axis_1)
    second_seed = np.asarray(system.axis_2, dtype=float)
    second = _unit(second_seed - np.dot(second_seed, first) * first)
    third = _unit(np.cross(first, second))
    return first, second, third


def _unit(value):
    vector = np.asarray(value, dtype=float)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1.0e-14 else np.asarray((1.0, 0.0, 0.0))


def _visible(scene, entity):
    visibility = getattr(getattr(scene, "owner", None), "visibility", None)
    return visibility is None or visibility.is_entity_visible(entity)
