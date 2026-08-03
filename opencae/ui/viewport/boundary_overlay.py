from __future__ import annotations

import numpy as np
import pyvista as pv

from .boundary_geometry import region_samples
from .screen_scale import world_size_for_pixels
from .safe_operations import add_interaction_observer, remove_actor

_AXES = np.eye(3)


class BoundaryOverlay:
    def __init__(self, owner):
        self.owner = owner; self._names = []; self._project = self._scene = None
        add_interaction_observer(owner.plotter.iren, "EndInteractionEvent", self._camera_changed)

    def clear(self, plotter):
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()

    def show(self, plotter, project, scene):
        self._project, self._scene = project, scene; self.clear(plotter)
        support_meshes, load_meshes, thermal_meshes = [], [], []
        for support in project.supports:
            for point, normal in region_samples(project, support.target, scene):
                support_meshes.extend(_support_glyphs(plotter, point, support))
        for load in project.loads:
            for point, normal in region_samples(project, load.target, scene):
                target = thermal_meshes if getattr(load, "load_type", "") == "Temperature" else load_meshes
                target.extend(_load_glyphs(plotter, point, normal, load))
        self._add_group(plotter, support_meshes, "supports", "#4aa3e8")
        self._add_group(plotter, load_meshes, "loads", "#ed6c63")
        self._add_group(plotter, thermal_meshes, "temperature", "#f2a45d")

    def _add_group(self, plotter, meshes, name, color):
        if not meshes: return
        actor_name = f"bc-{name}"; self._names.append(actor_name)
        plotter.add_mesh(pv.merge(meshes), color=color, lighting=False, pickable=False, name=actor_name, render=False)

    def _camera_changed(self, *_):
        if self._project is None or self._scene is None or self.owner.stage != "BOUNDARY CONDITIONS": return
        self.show(self.owner.plotter, self._project, self._scene); self.owner.plotter.render()


def _support_glyphs(plotter, point, support):
    scale = world_size_for_pixels(plotter, point, 24); result = []
    components = list(getattr(support, "components", ()) or ()) + [None] * 6
    active = [value is not None for value in components[:6]]
    if not any(active): active[:3] = [True, True, True]
    for index, axis in enumerate(_AXES):
        if active[index]:
            start = np.asarray(point) + axis * scale * 0.42
            result.append(pv.Arrow(start=start, direction=-axis, scale=scale * 0.42))
        if active[index + 3]: result.append(_ring(point, axis, scale * 0.32))
    return result


def _load_glyphs(plotter, point, normal, load):
    scale = world_size_for_pixels(plotter, point, 33)
    if getattr(load, "load_type", "") == "Temperature": return [pv.Sphere(radius=scale * 0.16, center=point)]
    result = []; vector = _load_vector(load, normal)
    if np.linalg.norm(vector) > 1e-14:
        direction = vector / np.linalg.norm(vector); start = np.asarray(point) - direction * scale
        result.append(pv.Arrow(start=start, direction=direction, scale=scale))
    for index, value in enumerate(list(getattr(load, "components", ()) or [])[3:6]):
        if abs(float(value)) > 1e-14: result.append(_ring(point, _AXES[index], scale * 0.32))
    return result


def _load_vector(load, normal):
    if getattr(load, "load_type", "") == "Pressure" and normal is not None:
        return -np.asarray(normal, float) * float(getattr(load, "pressure", 0.0))
    values = getattr(load, "components", None)
    if values: return np.asarray(values[:3], float)
    if getattr(load, "load_type", "") == "Inertia Load": return np.asarray(load.center_acceleration, float)
    return np.zeros(3)


def _ring(center, normal, radius):
    normal = np.asarray(normal, float); normal /= max(np.linalg.norm(normal), 1e-14)
    seed = np.array((1.0, 0.0, 0.0)) if abs(normal[0]) < 0.8 else np.array((0.0, 1.0, 0.0))
    first = np.cross(normal, seed); first /= np.linalg.norm(first); second = np.cross(normal, first)
    angles = np.linspace(0, 2 * np.pi, 33)
    points = np.asarray(center) + radius * (np.cos(angles)[:, None] * first + np.sin(angles)[:, None] * second)
    mesh = pv.PolyData(points); mesh.lines = np.asarray([len(points), *range(len(points))], dtype=np.int64); return mesh
