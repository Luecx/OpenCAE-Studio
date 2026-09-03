"""Render model coordinate systems at a fixed screen-space size."""

import numpy as np
import pyvista as pv

from opencae.ui.core.theme import PALETTE, VIEWPORT_FONT_FAMILY, VIEWPORT_FONT_SIZE
from .instance_transform import transform_points, transform_vector
from .safe_operations import remove_actor
from .screen_scale import world_size_for_pixels


class CoordinateSystemOverlay:
    """Draw visible coordinate systems and keep them constant in screen space."""

    def __init__(self):
        self._names = []
        self._records = []
        self._camera = None
        self._observer_id = None
        self._rescaling = False

    def _clear_actors(self, plotter):
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()

    def clear(self, plotter):
        self._clear_actors(plotter)
        self._records.clear()

    def show_part(self, plotter, part, scene=None):
        self._observe_camera(plotter)
        records = [
            (system, f"part-{index}", None)
            for index, system in enumerate(getattr(part, "coordinate_systems", ()))
            if _visible(scene, system)
        ]
        self._replace_records(plotter, records)

    def show_assembly(self, plotter, project, scene):
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
        """Replace visible systems without reacting to camera events caused by actors."""
        if self._rescaling:
            return
        self._rescaling = True
        try:
            self._clear_actors(plotter)
            self._records = list(records)
            self._redraw(plotter)
        finally:
            self._rescaling = False

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
        """Rebuild only coordinate-system actors using the current camera zoom."""
        if not self._records or self._rescaling:
            return False
        self._rescaling = True
        try:
            self._clear_actors(plotter)
            self._redraw(plotter)
        finally:
            self._rescaling = False
        return True

    def _redraw(self, plotter):
        for system, key, instance in self._records:
            self._draw(plotter, system, key, instance)

    def _draw(self, plotter, system, key, instance=None):
        origin = np.asarray(system.origin, dtype=float)
        x, y, z = self._axes(system)
        if instance:
            origin = transform_points([origin], instance)[0]
            x, y, z = (transform_vector(vector, instance) for vector in (x, y, z))
        scale = world_size_for_pixels(plotter, origin, 44)
        cylindrical = str(system.system_type).lower().startswith("cyl")
        labels = ("r", "θ", "z") if cylindrical else ("x", "y", "z")
        for suffix, vector, color, label in zip(
            ("x", "y", "z"),
            (x, y, z),
            (PALETTE["axis_x"], PALETTE["axis_y"], PALETTE["axis_z"]),
            labels,
        ):
            name = f"csys-{key}-{suffix}"
            self._names.append(name)
            arrow = pv.Arrow(start=origin, direction=vector, scale=scale)
            plotter.add_mesh(
                arrow,
                color=color,
                lighting=False,
                pickable=False,
                name=name,
                render=False,
            )
            tip = origin + vector * scale
            label_name = f"{name}-label"
            self._names.append(label_name)
            plotter.add_point_labels(
                np.asarray([tip]),
                [label],
                name=label_name,
                point_size=0,
                font_size=VIEWPORT_FONT_SIZE,
                font_family=VIEWPORT_FONT_FAMILY,
                text_color=color,
                shape_opacity=0,
                always_visible=False,
                render=False,
            )
        if cylindrical:
            self._ring(plotter, origin, z, scale * 0.48, key)
        label_name = f"csys-{key}-label"
        self._names.append(label_name)
        plotter.add_point_labels(
            np.asarray([origin]),
            [system.name],
            name=label_name,
            point_size=0,
            font_size=VIEWPORT_FONT_SIZE,
            font_family=VIEWPORT_FONT_FAMILY,
            text_color=PALETTE["overlay_text"],
            shape_color=PALETTE["overlay_bg"],
            shape_opacity=0.82,
            always_visible=False,
            render=False,
        )

    def _ring(self, plotter, origin, normal, radius, key):
        name = f"csys-{key}-ring"
        self._names.append(name)
        circle = _ring_geometry(origin, normal, radius)
        plotter.add_mesh(
            circle,
            color=PALETTE["accent_hover"],
            line_width=2,
            lighting=False,
            pickable=False,
            name=name,
            render=False,
        )

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


def _ring_geometry(origin, normal, radius):
    """Build a circular polyline in the plane orthogonal to ``normal``."""
    center = np.asarray(origin, dtype=float)
    axis = CoordinateSystemOverlay._unit(normal)
    reference = (
        np.asarray((1.0, 0.0, 0.0))
        if abs(float(axis[0])) < 0.9
        else np.asarray((0.0, 1.0, 0.0))
    )
    polar = CoordinateSystemOverlay._unit(np.cross(axis, reference)) * float(radius)
    return pv.CircularArcFromNormal(
        center=center,
        resolution=72,
        normal=axis,
        polar=polar,
        angle=360.0,
    )


def _visible(scene, entity):
    visibility = getattr(getattr(scene, "owner", None), "visibility", None)
    return visibility is None or visibility.is_entity_visible(entity)
