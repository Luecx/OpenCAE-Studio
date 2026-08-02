from __future__ import annotations

import numpy as np
import pyvista as pv

from .boundary_geometry import region_samples
from .screen_scale import world_size_for_pixels


class CouplingOverlay:
    def __init__(self):
        self._names = []

    def clear(self, plotter):
        for name in self._names:
            try:
                plotter.remove_actor(name, reset_camera=False, render=False)
            except Exception:
                pass
        self._names.clear()

    def show(self, plotter, project, scene):
        self.clear(plotter)
        for index, constraint in enumerate(project.assembly.constraints):
            if "Coupling" not in str(getattr(constraint, "constraint_type", "")):
                continue
            master_entity = project.try_resolve(constraint.master_ref)
            master_samples = region_samples(project, master_entity, scene, maximum=1)
            if not master_samples:
                continue
            master = np.asarray(master_samples[0][0], dtype=float)
            samples = [point for point, _normal in region_samples(project, constraint.slave_ref, scene, maximum=16)]
            if not samples:
                continue
            self._draw(plotter, master, samples, constraint, index)

    def _draw(self, plotter, master, samples, constraint, index):
        lines = []
        for offset, _sample in enumerate(samples):
            lines.extend((2, 2 * offset, 2 * offset + 1))
        coords = np.asarray([[value for point in (master, sample) for value in point] for sample in samples], float).reshape(-1, 3)
        mesh = pv.PolyData(coords)
        mesh.lines = np.asarray(lines, np.int64)
        color = "#64b5f6" if "Kinematic" in str(constraint.constraint_type) else "#9acb63"
        name = f"coupling-{index}"
        self._names.append(name)
        plotter.add_mesh(mesh, color=color, line_width=1.5, lighting=False, pickable=False, name=name, render=False)
        radius = world_size_for_pixels(plotter, master, 9)
        marker = f"{name}-master"
        self._names.append(marker)
        plotter.add_mesh(pv.Sphere(radius=radius, center=master), color=color, lighting=False, pickable=False, name=marker, render=False)
