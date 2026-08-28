"""Own persistent VTK actors and mutable label points for one coordinate system."""

from __future__ import annotations

import numpy as np
import pyvista as pv

from .safe_operations import remove_actor


class CoordinateSystemVisual:
    """Create one coordinate-system pipeline and update it through transforms."""

    def __init__(
        self,
        plotter,
        *,
        key: str,
        name: str,
        origin,
        axes,
        labels,
        cylindrical: bool,
    ):
        self.origin = np.asarray(origin, dtype=float)
        self._axes = tuple(np.asarray(axis, dtype=float) for axis in axes)
        self._actors = []
        self._scaled_actors = []
        self._axis_label_points = []
        self._create_axes(plotter, key, labels)
        if cylindrical:
            self._create_ring(plotter, key)
        self._create_label(
            plotter,
            f"csys-{key}-label",
            self.origin,
            name,
            font_size=10,
            text_color="#f0f3f6",
            shape_color="#20262d",
            shape_opacity=0.82,
        )

    def clear(self, plotter):
        """Remove this visual's persistent actors from the renderer."""
        for actor in self._actors:
            remove_actor(plotter, actor)
        self._actors.clear()
        self._scaled_actors.clear()
        self._axis_label_points.clear()

    def set_scale(self, scale: float):
        """Apply one world-space scale without replacing actors or mappers."""
        value = max(float(scale), 1e-9)
        for actor in self._scaled_actors:
            actor.SetScale(value, value, value)
        for points, axis in self._axis_label_points:
            points.points = np.asarray([self.origin + axis * value])

    def _create_axes(self, plotter, key, labels):
        colors = ("#ef6666", "#70d184", "#6ca6ff")
        for suffix, axis, color, label in zip(
            ("x", "y", "z"),
            self._axes,
            colors,
            labels,
        ):
            name = f"csys-{key}-{suffix}"
            arrow = pv.Arrow(start=(0.0, 0.0, 0.0), direction=axis, scale=1.0)
            actor = plotter.add_mesh(
                arrow,
                color=color,
                lighting=False,
                pickable=False,
                name=name,
                render=False,
            )
            actor.SetPosition(*self.origin)
            self._actors.append(actor)
            self._scaled_actors.append(actor)

            label_points = self._create_label(
                plotter,
                f"{name}-label",
                self.origin + axis,
                label,
                font_size=9,
                text_color=color,
                shape_opacity=0,
            )
            self._axis_label_points.append((label_points, axis))

    def _create_ring(self, plotter, key):
        name = f"csys-{key}-ring"
        actor = plotter.add_mesh(
            ring_geometry((0.0, 0.0, 0.0), self._axes[2], 0.48),
            color="#8fd3ff",
            line_width=2,
            lighting=False,
            pickable=False,
            name=name,
            render=False,
        )
        actor.SetPosition(*self.origin)
        self._actors.append(actor)
        self._scaled_actors.append(actor)

    def _create_label(
        self,
        plotter,
        name,
        point,
        text,
        *,
        font_size,
        text_color,
        shape_color="grey",
        shape_opacity,
    ):
        points = pv.PolyData(np.asarray([point], dtype=float))
        points["labels"] = np.asarray([str(text)])
        actor = plotter.add_point_labels(
            points,
            "labels",
            name=name,
            show_points=False,
            font_size=font_size,
            text_color=text_color,
            shape_color=shape_color,
            shape_opacity=shape_opacity,
            always_visible=False,
            render=False,
        )
        self._actors.append(actor)
        return points


def ring_geometry(origin, normal, radius):
    """Build a circular polyline in the plane orthogonal to ``normal``."""
    center = np.asarray(origin, dtype=float)
    axis = _unit(normal)
    reference = (
        np.asarray((1.0, 0.0, 0.0))
        if abs(float(axis[0])) < 0.9
        else np.asarray((0.0, 1.0, 0.0))
    )
    polar = _unit(np.cross(axis, reference)) * float(radius)
    return pv.CircularArcFromNormal(
        center=center,
        resolution=72,
        normal=axis,
        polar=polar,
        angle=360.0,
    )


def _unit(value):
    vector = np.asarray(value, dtype=float)
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 1e-14 else np.asarray((1.0, 0.0, 0.0))
