from __future__ import annotations

import numpy as np
import pyvista as pv

from .assembly_context import ActorReference
from .instance_transform import transform_points
from .surface_shading import face_color

FACE_COLOR = "#7f8d99"
EDGE_COLOR = "#1b232b"
VERTEX_COLOR = "#d7dde3"
SELECTED_COLOR = "#3296e6"
_BASE_COLORS = {}


def add_geometry(plotter, snapshot, instance=None):
    faces, edges, vertices = {}, {}, {}
    prefix = f"{instance.name}-" if instance else ""
    for patch in snapshot.surfaces:
        points = transform_points(patch.points, instance) if instance else patch.points
        mesh = pv.PolyData(points, patch.faces)
        color = face_color(mesh, patch.tag)
        actor = plotter.add_mesh(
            mesh, color=color, show_edges=False, lighting=True,
            smooth_shading=True, ambient=0.20, diffuse=0.78,
            specular=0.06, specular_power=10.0, pickable=True,
            name=f"{prefix}face-{patch.tag}", render=False,
        )
        _BASE_COLORS[actor] = color
        faces[actor] = ActorReference(instance.name if instance else None, 2, patch.tag, instance.id if instance else None)
    for patch in snapshot.edges:
        points = transform_points(patch.points, instance) if instance else patch.points
        mesh = pv.PolyData(points); mesh.lines = patch.lines
        actor = plotter.add_mesh(
            mesh, color=EDGE_COLOR, line_width=2.0, lighting=False,
            render_lines_as_tubes=False, pickable=True,
            name=f"{prefix}edge-{patch.tag}", render=False,
        )
        edges[actor] = ActorReference(instance.name if instance else None, 1, patch.tag, instance.id if instance else None)
    for patch in snapshot.vertices:
        point = transform_points(np.asarray([patch.point]), instance)[0] if instance else patch.point
        actor = plotter.add_mesh(
            pv.PolyData([point]), color=VERTEX_COLOR, point_size=8.0,
            render_points_as_spheres=True, lighting=False, pickable=True,
            name=f"{prefix}vertex-{patch.tag}", render=False,
        )
        vertices[actor] = ActorReference(instance.name if instance else None, 0, patch.tag, instance.id if instance else None)
    return faces, edges, vertices


def set_actor_selected(actor, selected: bool, kind: str = "face"):
    base = _BASE_COLORS.get(actor, {
        "face": FACE_COLOR, "edge": EDGE_COLOR, "vertex": VERTEX_COLOR, "rp": "#f3b65b",
    }.get(kind, FACE_COLOR))
    color = SELECTED_COLOR if selected else base
    rgb = color if isinstance(color, tuple) else pv.Color(color).float_rgb
    actor.GetProperty().SetColor(rgb)
    if kind == "edge": actor.GetProperty().SetLineWidth(4.0 if selected else 2.0)
    if kind == "vertex": actor.GetProperty().SetPointSize(13.0 if selected else 8.0)
    if kind == "rp": actor.GetProperty().SetPointSize(20.0 if selected else 15.0)
