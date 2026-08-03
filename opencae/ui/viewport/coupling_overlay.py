from __future__ import annotations

import numpy as np
import pyvista as pv

from opencae.model.entities.constraints import DistributingCoupling, KinematicCoupling
from .boundary_geometry import region_samples
from .safe_operations import remove_actor
from .screen_scale import world_size_for_pixels


class CouplingOverlay:
    def __init__(self):
        self._names = []

    def clear(self, plotter):
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()

    def show(self, plotter, project, scene):
        self.clear(plotter)
        selected_id = getattr(
            getattr(scene.owner.store, "selection", None), "id", None
        )
        for index, constraint in enumerate(project.assembly.constraints):
            if not isinstance(
                constraint, (KinematicCoupling, DistributingCoupling)
            ):
                continue
            master_samples = region_samples(
                project, constraint.control_point, scene, maximum=1
            )
            slave_samples = region_samples(
                project, constraint.slave, scene, maximum=16
            )
            if not master_samples or not slave_samples:
                continue
            master = np.asarray(master_samples[0][0], dtype=float)
            self._draw(
                plotter,
                master,
                [point for point, _normal in slave_samples],
                constraint,
                index,
                selected=getattr(constraint, "id", None) == selected_id,
            )

    def _draw(self, plotter, master, samples, constraint, index, *, selected=False):
        lines = []
        for offset, _sample in enumerate(samples):
            lines.extend((2, 2 * offset, 2 * offset + 1))
        coords = np.asarray(
            [[value for point in (master, sample) for value in point] for sample in samples],
            float,
        ).reshape(-1, 3)
        mesh = pv.PolyData(coords)
        mesh.lines = np.asarray(lines, np.int64)
        color = (
            "#64b5f6"
            if isinstance(constraint, KinematicCoupling)
            else "#9acb63"
        )
        name = f"coupling-{constraint.id or index}"
        self._names.append(name)
        plotter.add_mesh(
            mesh,
            color=color,
            line_width=3.4 if selected else 1.5,
            opacity=1.0 if selected else .72,
            lighting=False,
            pickable=False,
            name=name,
            render=False,
        )
        radius = world_size_for_pixels(plotter, master, 13 if selected else 9)
        marker = f"{name}-master"
        self._names.append(marker)
        plotter.add_mesh(
            pv.Sphere(radius=radius, center=master),
            color="#ffd166" if selected else color,
            opacity=1.0 if selected else .82,
            lighting=False,
            pickable=False,
            name=marker,
            render=False,
        )
