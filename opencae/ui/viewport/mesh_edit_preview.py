"""Transient viewport preview used by interactive mesh editing dialogs."""

from __future__ import annotations

import numpy as np

from opencae.model.entities.fem import MeshEntityOrigin
from opencae.ui.core.theme import PALETTE
from .safe_operations import remove_actor


_AVAILABLE_POINT_ACTOR = "mesh-edit-preview-available-points"
_POINT_ACTOR = "mesh-edit-preview-points"
_LINE_ACTOR = "mesh-edit-preview-lines"
_POSITION_ACTOR = "mesh-edit-preview-position"


def clear_mesh_edit_preview(viewport, *, render=True) -> None:
    plotter = getattr(viewport, "plotter", None)
    if plotter is None:
        return
    remove_actor(plotter, _AVAILABLE_POINT_ACTOR, render=False)
    remove_actor(plotter, _POINT_ACTOR, render=False)
    remove_actor(plotter, _LINE_ACTOR, render=False)
    remove_actor(plotter, _POSITION_ACTOR, render=False)
    if render:
        try:
            plotter.render()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass


def show_position_preview(viewport, position) -> None:
    plotter = getattr(viewport, "plotter", None)
    if plotter is None or position is None:
        return
    remove_actor(plotter, _POSITION_ACTOR, render=False)
    point = np.asarray([tuple(float(value) for value in position)], dtype=float)
    try:
        plotter.add_points(
            point,
            color=PALETTE["selection_3d"],
            point_size=18,
            render_points_as_spheres=True,
            name=_POSITION_ACTOR,
            pickable=False,
            reset_camera=False,
            render=False,
        )
        plotter.render()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return


def show_connectivity_preview(viewport, mesh, node_ids, element_type=None) -> None:
    plotter = getattr(viewport, "plotter", None)
    if plotter is None:
        return
    remove_actor(plotter, _AVAILABLE_POINT_ACTOR, render=False)
    remove_actor(plotter, _POINT_ACTOR, render=False)
    remove_actor(plotter, _LINE_ACTOR, render=False)

    selected_ids = set()
    points = []
    for node_id in node_ids or ():
        try:
            node_id = int(node_id)
            points.append(mesh.node(node_id).coordinates)
            selected_ids.add(node_id)
        except (KeyError, TypeError, ValueError):
            continue

    # Authored nodes are persistent scene actors. Only generated/imported nodes
    # need this temporary point cloud while an element connectivity is picked.
    available_points = []
    try:
        available_points = [
            coordinates
            for node_id, coordinates, origin in zip(
                mesh.nodes.ids,
                mesh.nodes.coordinates,
                mesh.nodes.origins,
                strict=True,
            )
            if int(node_id) not in selected_ids
            and MeshEntityOrigin.coerce(origin) != MeshEntityOrigin.AUTHORED
        ]
    except (AttributeError, TypeError, ValueError):
        available_points = []

    try:
        if available_points:
            plotter.add_points(
                np.asarray(available_points, dtype=float),
                color=PALETTE["cad_vertex"],
                point_size=11,
                render_points_as_spheres=True,
                lighting=False,
                name=_AVAILABLE_POINT_ACTOR,
                pickable=False,
                reset_camera=False,
                render=False,
            )

        if not points:
            plotter.render()
            return

        array = np.asarray(points, dtype=float)
        plotter.add_points(
            array,
            color=PALETTE["selection_3d"],
            point_size=15,
            render_points_as_spheres=True,
            name=_POINT_ACTOR,
            pickable=False,
            reset_camera=False,
            render=False,
        )
        if len(array) >= 2:
            segments = []
            for first, second in zip(array[:-1], array[1:]):
                segments.extend((first, second))
            expected = getattr(element_type, "node_count", None)
            name = getattr(element_type, "__name__", "")
            closes = bool(
                len(array) >= 3
                and expected == len(array)
                and name not in {"Tet4", "Pyramid5", "Wedge6", "Hex8"}
            )
            if closes:
                segments.extend((array[-1], array[0]))
            plotter.add_lines(
                np.asarray(segments, dtype=float),
                color=PALETTE["selection_3d"],
                width=3,
                name=_LINE_ACTOR,
                pickable=False,
                reset_camera=False,
                render=False,
            )
        plotter.render()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return
