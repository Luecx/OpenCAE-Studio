"""Renders saved element densities for topology iterations in the viewport."""

from __future__ import annotations

import numpy as np
import pyvista as pv

from .safe_operations import remove_actor
from .vtk_cell_data import cell_array

_THRESHOLD_ABSOLUTE_TOLERANCE = 1.0e-9
_THRESHOLD_RELATIVE_TOLERANCE = 1.0e-9


class TopologyDensityOverlay:
    """Display one saved topology iteration on the current assembly mesh."""

    def __init__(self):
        self._names: list[str] = []
        self._hidden_base_actors = []

    def clear(self, viewport, *, render=True):
        plotter = getattr(viewport, "plotter", None)
        if plotter is None:
            return
        for name in self._names:
            remove_actor(plotter, name)
        self._names.clear()
        for actor in self._hidden_base_actors:
            try:
                actor.SetVisibility(True)
            except (AttributeError, RuntimeError):
                pass
        self._hidden_base_actors.clear()
        if render:
            plotter.render()

    def show(
        self,
        viewport,
        run,
        iteration,
        mesh_index,
        density,
        *,
        threshold=0.30,
    ):
        self.clear(viewport, render=False)
        scene = viewport.scene
        values = np.asarray(density, dtype=float).ravel()
        if len(values) != mesh_index.count:
            raise ValueError(
                "Saved topology density does not match the current mesh manifest"
            )
        pieces = []
        for instance_id, grid in scene.mesh_grids.items():
            if grid is None or not grid.n_cells:
                continue
            element_ids = cell_array(grid, "element_id")
            if not len(element_ids):
                continue
            rows = np.where(
                np.asarray(mesh_index.instance_ids) == str(instance_id)
            )[0]
            lookup = {
                int(mesh_index.source_element_ids[row]): float(values[row])
                for row in rows
            }
            cell_density = np.asarray(
                [
                    lookup.get(int(element_id), np.nan)
                    for element_id in element_ids
                ],
                dtype=float,
            )
            keep = visible_density_indices(cell_density, threshold)
            if not len(keep):
                continue
            copy = grid.copy(deep=False)
            copy.cell_data["Topology Density"] = cell_density
            pieces.append(copy.extract_cells(keep))

        if (
            not pieces
            and not scene.mesh_grids
            and scene.mesh_grid is not None
            and scene.mesh_grid.n_cells
        ):
            grid = scene.mesh_grid
            element_ids = cell_array(grid, "element_id")
            lookup = {
                int(element_id): float(value)
                for element_id, value in zip(
                    mesh_index.source_element_ids,
                    values,
                )
            }
            cell_density = np.asarray(
                [
                    lookup.get(int(element_id), np.nan)
                    for element_id in element_ids
                ],
                dtype=float,
            )
            keep = visible_density_indices(cell_density, threshold)
            if len(keep):
                copy = grid.copy(deep=False)
                copy.cell_data["Topology Density"] = cell_density
                pieces.append(copy.extract_cells(keep))

        for actor in [scene.mesh_actor, *scene.mesh_actors]:
            if actor is None:
                continue
            try:
                actor.SetVisibility(False)
                self._hidden_base_actors.append(actor)
            except (AttributeError, RuntimeError):
                pass

        if pieces:
            merged = pv.merge(pieces, merge_points=False)
            name = "topology-density"
            viewport.plotter.add_mesh(
                merged,
                scalars="Topology Density",
                preference="cell",
                clim=(0.0, 1.0),
                cmap="viridis",
                show_edges=True,
                edge_color="#27323b",
                line_width=0.7,
                lighting=True,
                ambient=0.72,
                diffuse=0.28,
                specular=0.0,
                name=name,
                pickable=False,
                reset_camera=False,
                render=False,
                scalar_bar_args={
                    "title": "Density",
                    "vertical": True,
                },
            )
            self._names.append(name)

        finite = values[np.isfinite(values)]
        density_text = (
            f"ρ min/mean/max "
            f"{np.min(finite):.3f}/{np.mean(finite):.3f}/{np.max(finite):.3f}"
            if len(finite)
            else "ρ unavailable"
        )
        label = (
            f"Iteration {iteration.number}   "
            f"Objective {iteration.objective_value:.6g}   "
            f"Threshold {float(threshold):.3f}   "
            f"{density_text}"
        )
        label_name = "topology-density-label"
        viewport.plotter.add_text(
            label,
            position="upper_left",
            font_size=10,
            name=label_name,
            render=False,
        )
        self._names.append(label_name)
        viewport.plotter.render()


def visible_density_indices(density, threshold):
    """Return stable visible indices for a floating-point density threshold."""

    values = np.asarray(density, dtype=float).ravel()
    limit = float(threshold)
    tolerance = max(
        _THRESHOLD_ABSOLUTE_TOLERANCE,
        abs(limit) * _THRESHOLD_RELATIVE_TOLERANCE,
    )
    return np.flatnonzero(
        np.isfinite(values)
        & (values >= limit - tolerance)
    )
