from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.datums import DatumPlane, DatumPoint, DatumVector
from opencae.model.selection import SelectableKind, ViewportHit
from opencae.ui.core.theme import PALETTE
from .instance_transform import transform_points, transform_vector
from .screen_scale import world_size_for_pixels
from .safe_operations import remove_actor


class DatumOverlay:
    def __init__(self, namespace="model-datum"):
        # Every overlay owner needs its own actor namespace. Preview and model
        # datums used to share names such as ``datum-point-part-0``; clearing a
        # dialog preview could therefore remove the permanent scene actor.
        self.namespace = str(namespace).strip() or "datum"
        self._names = []

    def clear(self, plotter):
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()

    def show_part(self, plotter, part, scene):
        self.clear(plotter)
        for index, datum in enumerate(getattr(part, "datums", ())):
            if _visible(scene, datum):
                self._draw(plotter, scene, datum, f"part-{index}")

    def show_assembly(self, plotter, project, scene):
        self.clear(plotter)
        for instance_id, instance in scene.assembly_instances.items():
            part = project.try_resolve(instance.part_ref)
            if part:
                for index, datum in enumerate(getattr(part, "datums", ())):
                    if _visible(scene, datum):
                        self._draw(plotter, scene, datum, f"{instance_id}-{index}", instance, instance.name)

    def _actor_name(self, kind, key):
        return f"{self.namespace}-{kind}-{key}"

    def _draw(self, plotter, scene, datum, key, instance=None, instance_name=None):
        if isinstance(datum, DatumPoint):
            self._point(plotter, scene, datum, key, instance, instance_name)
        elif isinstance(datum, DatumVector):
            self._vector(plotter, scene, datum, key, instance, instance_name)
        elif isinstance(datum, DatumPlane):
            self._plane(plotter, scene, datum, key, instance)

    def _point(self, plotter, scene, datum, key, instance, instance_name):
        position = self._point_transform(datum.position, instance)
        name = self._actor_name("point", key)
        self._names.append(name)
        actor = plotter.add_mesh(
            pv.PolyData([position]),
            color=PALETTE["datum"],
            point_size=15,
            render_points_as_spheres=True,
            lighting=False,
            pickable=True,
            name=name,
            render=False,
        )
        self._prefer_coincident_point(actor)
        label = f"{instance_name}.{datum.name}" if instance_name else datum.name
        scene.datum_actors[actor] = ViewportHit(
            kind=SelectableKind.DATUM_POINT,
            entity_id=datum.id,
            instance_id=getattr(instance, "id", None),
            world_position=tuple(position),
            dimension=0,
            label=label,
        )
        self._label(plotter, position, datum.name, name, boxed=True)

    def _vector(self, plotter, scene, datum, key, instance, instance_name):
        origin = self._point_transform(datum.origin, instance)
        direction = self._vector_transform(datum.direction, instance)
        scale = world_size_for_pixels(plotter, origin, 55)
        name = self._actor_name("vector", key)
        self._names.append(name)
        actor = plotter.add_mesh(
            pv.Arrow(start=origin, direction=direction, scale=scale),
            color=PALETTE["datum_vector"],
            lighting=False,
            pickable=True,
            name=name,
            render=False,
        )
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
        mesh = pv.PolyData(points, np.asarray([4, 0, 1, 2, 3]))
        name = self._actor_name("plane", key)
        self._names.append(name)
        actor = plotter.add_mesh(
            mesh,
            color=PALETTE["datum_plane"],
            opacity=.16,
            show_edges=True,
            edge_color=PALETTE["datum_plane_edge"],
            line_width=1.8,
            lighting=False,
            pickable=True,
            name=name,
            render=False,
        )
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
        snapshots = getattr(scene, "assembly_snapshots", {}) or {}
        snapshot = getattr(scene, "snapshot", None) if instance is None else snapshots.get(getattr(instance, "id", ""))
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
    def _prefer_coincident_point(actor):
        try:
            mapper = actor.GetMapper()
            mapper.SetResolveCoincidentTopologyToPolygonOffset()
            mapper.SetRelativeCoincidentTopologyPointOffsetParameter(-2.0)
        except (AttributeError, RuntimeError, TypeError):
            pass

    @staticmethod
    def _unit(vector):
        value = np.asarray(vector, dtype=float)
        length = float(np.linalg.norm(value))
        if length <= 1.0e-14:
            return np.asarray((1.0, 0.0, 0.0), dtype=float)
        return value / length

    def _label(self, plotter, point, text, prefix, boxed=False):
        name = prefix + "-label"
        self._names.append(name)
        options = dict(
            name=name,
            point_size=0,
            show_points=False,
            font_size=10,
            text_color=PALETTE["overlay_text"],
            always_visible=True,
            render=False,
        )
        if boxed:
            options.update(shape_color=PALETTE["overlay_bg"], shape_opacity=.84)
        else:
            options.update(shape=None)
        plotter.add_point_labels(np.asarray([point]), [text], **options)

    @staticmethod
    def _point_transform(point, instance):
        return transform_points([point], instance)[0] if instance else np.asarray(point, float)

    @staticmethod
    def _vector_transform(vector, instance):
        return transform_vector(vector, instance) if instance else np.asarray(vector, float)


def _visible(scene, entity):
    visibility = getattr(getattr(scene, "owner", None), "visibility", None)
    return visibility is None or visibility.is_entity_visible(entity)
