from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.datums import DatumPlane, DatumPoint, DatumVector
from opencae.model.selection import SelectableKind, ViewportHit
from .instance_transform import transform_points, transform_vector
from .screen_scale import world_size_for_pixels
from .safe_operations import remove_actor


class DatumOverlay:
    def __init__(self): self._names = []

    def clear(self, plotter):
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()

    def show_part(self, plotter, part, scene):
        self.clear(plotter)
        for index, datum in enumerate(getattr(part, "datums", ())): self._draw(plotter, scene, datum, f"part-{index}")

    def show_assembly(self, plotter, project, scene):
        self.clear(plotter)
        for instance_id, instance in scene.assembly_instances.items():
            part = project.try_resolve(instance.part_ref)
            if part:
                for index, datum in enumerate(getattr(part, "datums", ())):
                    self._draw(plotter, scene, datum, f"{instance_id}-{index}", instance, instance.name)

    def _draw(self, plotter, scene, datum, key, instance=None, instance_name=None):
        if isinstance(datum, DatumPoint): self._point(plotter, scene, datum, key, instance, instance_name)
        elif isinstance(datum, DatumVector): self._vector(plotter, scene, datum, key, instance, instance_name)
        elif isinstance(datum, DatumPlane): self._plane(plotter, scene, datum, key, instance)

    def _point(self, plotter, scene, datum, key, instance, instance_name):
        position = self._point_transform(datum.position, instance); name = f"datum-point-{key}"; self._names.append(name)
        actor = plotter.add_mesh(pv.PolyData([position]), color="#f2cc60", point_size=12,
                                 render_points_as_spheres=True, lighting=False, pickable=True, name=name, render=False)
        label = f"{instance_name}.{datum.name}" if instance_name else datum.name
        scene.datum_actors[actor] = ViewportHit(
            kind=SelectableKind.DATUM_POINT,
            entity_id=datum.id,
            instance_id=getattr(instance, "id", None),
            world_position=tuple(position),
            dimension=0,
            label=label,
        )
        self._label(plotter, position, datum.name, name)

    def _vector(self, plotter, scene, datum, key, instance, instance_name):
        origin = self._point_transform(datum.origin, instance); direction = self._vector_transform(datum.direction, instance)
        scale = world_size_for_pixels(plotter, origin, 55); name = f"datum-vector-{key}"; self._names.append(name)
        actor = plotter.add_mesh(pv.Arrow(start=origin, direction=direction, scale=scale), color="#63c7d8",
                                 lighting=False, pickable=True, name=name, render=False)
        label = f"{instance_name}.{datum.name}" if instance_name else datum.name
        scene.datum_actors[actor] = ViewportHit(
            kind=SelectableKind.DATUM_VECTOR,
            entity_id=datum.id,
            instance_id=getattr(instance, "id", None),
            world_position=tuple(origin),
            dimension=-1,
            label=label,
        )
        self._label(plotter, origin + direction * scale, datum.name, name)

    def _plane(self, plotter, scene, datum, key, instance):
        origin = self._point_transform(datum.origin, instance)
        normal = self._unit(self._vector_transform(datum.normal, instance))
        axis = self._unit(self._vector_transform(datum.axis, instance))
        second = self._unit(np.cross(normal, axis))
        axis = self._unit(np.cross(second, normal))
        width, height = self._plane_size(plotter, scene, instance, origin, axis, second)
        points = np.asarray([
            origin + .5 * width * sx * axis + .5 * height * sy * second
            for sx, sy in ((-1., -1.), (1., -1.), (1., 1.), (-1., 1.))
        ])
        mesh = pv.PolyData(points, np.asarray([4, 0, 1, 2, 3])); name = f"datum-plane-{key}"; self._names.append(name)
        actor = plotter.add_mesh(mesh, color="#8f78d8", opacity=.16, show_edges=True, edge_color="#b7a7ef",
                         line_width=1.8, lighting=False, pickable=True, name=name, render=False)
        instance_name = getattr(instance, "name", None)
        label = f"{instance_name}.{datum.name}" if instance_name else datum.name
        scene.datum_actors[actor] = ViewportHit(
            kind=SelectableKind.DATUM_PLANE,
            entity_id=datum.id,
            instance_id=getattr(instance, "id", None),
            world_position=tuple(origin),
            dimension=2,
            label=label,
        )
        self._label(plotter, points[2], datum.name, name)

    def _plane_size(self, plotter, scene, instance, origin, axis, second):
        snapshot = scene.snapshot if instance is None else scene.assembly_snapshots.get(getattr(instance, "id", ""))
        bounds = getattr(snapshot, "bounds", None)
        if not bounds:
            fallback = world_size_for_pixels(plotter, origin, 260)
            return fallback, fallback
        x0, y0, z0, x1, y1, z1 = (float(value) for value in bounds)
        corners = np.asarray([
            (x, y, z)
            for x in (x0, x1)
            for y in (y0, y1)
            for z in (z0, z1)
        ], dtype=float)
        if instance is not None:
            corners = transform_points(corners, instance)
        relative = corners - np.asarray(origin, dtype=float)
        diagonal = float(np.linalg.norm(corners.max(axis=0) - corners.min(axis=0)))
        minimum = max(.55 * diagonal, world_size_for_pixels(plotter, origin, 180))
        width = max(2.30 * float(np.max(np.abs(relative @ axis))), minimum)
        height = max(2.30 * float(np.max(np.abs(relative @ second))), minimum)
        return width, height

    @staticmethod
    def _unit(vector):
        value = np.asarray(vector, dtype=float)
        length = float(np.linalg.norm(value))
        if length <= 1.0e-14:
            return np.asarray((1.0, 0.0, 0.0), dtype=float)
        return value / length

    def _label(self, plotter, point, text, prefix):
        name = prefix + "-label"; self._names.append(name)
        plotter.add_point_labels(np.asarray([point]), [text], name=name, point_size=0, show_points=False,
                                 font_size=10, text_color="#f7f9fb", shape=None, always_visible=True, render=False)

    @staticmethod
    def _point_transform(point, instance): return transform_points([point], instance)[0] if instance else np.asarray(point, float)
    @staticmethod
    def _vector_transform(vector, instance): return transform_vector(vector, instance) if instance else np.asarray(vector, float)
