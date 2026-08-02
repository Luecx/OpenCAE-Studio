from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.datums import DatumPlane, DatumPoint, DatumVector
from .instance_transform import transform_points, transform_vector
from .screen_scale import world_size_for_pixels


class DatumOverlay:
    def __init__(self): self._names = []

    def clear(self, plotter):
        for name in self._names:
            try: plotter.remove_actor(name, reset_camera=False, render=False)
            except Exception: pass
        self._names.clear()

    def show_part(self, plotter, part, scene):
        self.clear(plotter)
        for index, datum in enumerate(getattr(part, "datums", ())): self._draw(plotter, scene, datum, f"part-{index}")

    def show_assembly(self, plotter, project, scene):
        self.clear(plotter)
        for instance_name, instance in scene.assembly_instances.items():
            part = project.try_resolve(instance.part_ref)
            if part:
                for index, datum in enumerate(getattr(part, "datums", ())):
                    self._draw(plotter, scene, datum, f"{instance_name}-{index}", instance, instance_name)

    def _draw(self, plotter, scene, datum, key, instance=None, instance_name=None):
        if isinstance(datum, DatumPoint): self._point(plotter, scene, datum, key, instance, instance_name)
        elif isinstance(datum, DatumVector): self._vector(plotter, scene, datum, key, instance, instance_name)
        elif isinstance(datum, DatumPlane): self._plane(plotter, scene, datum, key, instance)

    def _point(self, plotter, scene, datum, key, instance, instance_name):
        position = self._point_transform(datum.position, instance); name = f"datum-point-{key}"; self._names.append(name)
        actor = plotter.add_mesh(pv.PolyData([position]), color="#f2cc60", point_size=12,
                                 render_points_as_spheres=True, lighting=False, pickable=True, name=name, render=False)
        label = f"{instance_name}.{datum.name}" if instance_name else datum.name
        scene.datum_actors[actor] = {"name": label, "kind": "datum_point", "dimension": 0,
                                    "tag": datum.id, "instance": instance_name, "instance_id": getattr(instance, "id", None), "point": tuple(position)}
        self._label(plotter, position, datum.name, name)

    def _vector(self, plotter, scene, datum, key, instance, instance_name):
        origin = self._point_transform(datum.origin, instance); direction = self._vector_transform(datum.direction, instance)
        scale = world_size_for_pixels(plotter, origin, 55); name = f"datum-vector-{key}"; self._names.append(name)
        actor = plotter.add_mesh(pv.Arrow(start=origin, direction=direction, scale=scale), color="#63c7d8",
                                 lighting=False, pickable=True, name=name, render=False)
        label = f"{instance_name}.{datum.name}" if instance_name else datum.name
        scene.datum_actors[actor] = {"name": label, "kind": "datum_vector", "dimension": -1, "tag": datum.id,
                                    "instance": instance_name, "instance_id": getattr(instance, "id", None), "point": tuple(origin), "direction": tuple(direction)}
        self._label(plotter, origin + direction * scale, datum.name, name)

    def _plane(self, plotter, scene, datum, key, instance):
        origin = self._point_transform(datum.origin, instance); normal = self._vector_transform(datum.normal, instance)
        axis = self._vector_transform(datum.axis, instance); size = world_size_for_pixels(plotter, origin, 100)
        second = np.cross(normal, axis); points = np.asarray([origin + size * (sx * axis + sy * second) for sx, sy in ((-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5))])
        mesh = pv.PolyData(points, np.asarray([4, 0, 1, 2, 3])); name = f"datum-plane-{key}"; self._names.append(name)
        actor = plotter.add_mesh(mesh, color="#8f78d8", opacity=.22, show_edges=True, edge_color="#b7a7ef",
                         line_width=1.5, lighting=False, pickable=True, name=name, render=False)
        scene.datum_actors[actor] = {"name":datum.name,"kind":"datum_plane","dimension":2,"tag":datum.id,
                                    "point":tuple(origin),"origin":tuple(origin),"normal":tuple(normal),"direction":tuple(normal)}
        self._label(plotter, origin, datum.name, name)

    def _label(self, plotter, point, text, prefix):
        name = prefix + "-label"; self._names.append(name)
        plotter.add_point_labels(np.asarray([point]), [text], name=name, point_size=0, show_points=False,
                                 font_size=10, text_color="#f7f9fb", shape=None, always_visible=True, render=False)

    @staticmethod
    def _point_transform(point, instance): return transform_points([point], instance)[0] if instance else np.asarray(point, float)
    @staticmethod
    def _vector_transform(vector, instance): return transform_vector(vector, instance) if instance else np.asarray(vector, float)
